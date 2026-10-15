package com.sih26190.dms.foli;

import com.fasterxml.jackson.databind.*;
import java.net.*;
import java.net.http.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.CancellationException;
import org.springframework.ai.chat.messages.*;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.ollama.OllamaChatModel;
import org.springframework.ai.ollama.api.*;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.core.retry.RetryTemplate;
import org.springframework.core.retry.RetryPolicy;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

/** All inference transport is fixed to numeric loopback, no redirects/proxies/tools. */
@Service
public class FoliLocalModel {
  private final FoliProperties config;
  private final URI base;
  private final HttpClient http;
  private final OllamaChatModel model;
  private final ObjectMapper json = new ObjectMapper();
  public record Reply(String text, long milliseconds, long outputTokens) {}

  public FoliLocalModel(FoliProperties config) {
    this.config = config; this.base = localOrigin(config.getOllamaUrl());
    http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3))
        .followRedirects(HttpClient.Redirect.NEVER).proxy(new ProxySelector() {
          @Override public List<Proxy> select(URI uri) {
            if (!uri.getHost().equals(base.getHost()) || uri.getPort()!=base.getPort())
              throw new IllegalArgumentException("Foli transport is loopback-only");
            return List.of(Proxy.NO_PROXY);
          }
          @Override public void connectFailed(URI uri, SocketAddress address, java.io.IOException e) {}
        }).build();
    var factory = new JdkClientHttpRequestFactory(http);
    factory.setReadTimeout(Duration.ofSeconds(config.getModelTimeoutSeconds()));
    var api = OllamaApi.builder().baseUrl(base.toString())
        .restClientBuilder(RestClient.builder().requestFactory(factory)).build();
    model = OllamaChatModel.builder().ollamaApi(api)
        .retryTemplate(new RetryTemplate(RetryPolicy.withMaxRetries(0)))
        .options(options(false)).build();
  }

  static URI localOrigin(String value) {
    try {
      var uri = URI.create(value);
      if (!"http".equals(uri.getScheme()) || !Set.of("127.0.0.1", "[::1]").contains(uri.getHost())
          || uri.getPort()<1 || uri.getUserInfo()!=null || uri.getRawQuery()!=null || uri.getFragment()!=null
          || !(uri.getPath().isEmpty() || uri.getPath().equals("/"))) throw new IllegalArgumentException();
      return URI.create(value.endsWith("/") ? value.substring(0,value.length()-1) : value);
    } catch (Exception e) { throw new IllegalArgumentException("Foli requires a numeric HTTP loopback Ollama origin with an explicit port"); }
  }

  private OllamaChatOptions options(boolean structured) {
    var options = OllamaChatOptions.builder().model(config.getModel()).temperature(0.1)
        .numCtx(config.getContextTokens()).numPredict(config.getOutputTokens()).keepAlive("10m")
        .disableThinking();
    if (structured) options.format("json");
    return options.build();
  }

  JsonNode get(String path) throws Exception {
    if (!Set.of("/api/tags", "/api/status", "/api/version", "/api/ps").contains(path)) throw new IllegalArgumentException();
    var request=HttpRequest.newBuilder(base.resolve(path)).timeout(Duration.ofSeconds(4)).GET().build();
    var response=http.send(request,HttpResponse.BodyHandlers.ofString());
    if (response.statusCode()!=200 || response.body().length()>1_000_000) throw new java.io.IOException();
    return json.readTree(response.body());
  }

  public Map<String,Object> health() {
    var result=new LinkedHashMap<String,Object>(); result.put("model",config.getModel()); result.put("loopbackOnly",true);
    try {
      boolean disabled=get("/api/status").path("cloud").path("disabled").asBoolean(false);
      result.put("cloudDisabled",disabled);
      JsonNode installed=null;
      for (var candidate:get("/api/tags").path("models"))
        if (candidate.path("name").asText().equals(config.getModel())) installed=candidate;
      boolean sizeOK=installed!=null && installed.path("size").asLong()>0 && installed.path("size").asLong()<6_000_000_000L;
      String status=!disabled?"CLOUD_NOT_DISABLED":installed==null?"MODEL_MISSING":!sizeOK?"MODEL_SIZE_LIMIT":"READY";
      result.put("status",status);
      if (installed!=null) { result.put("packageBytes",installed.path("size").asLong()); result.put("digest",installed.path("digest").asText()); }
    } catch (Exception e) { result.put("status","OFFLINE"); result.put("cloudDisabled",false); }
    return result;
  }

  public Reply ask(String system, String prompt, boolean structured) {
    FoliExtractionService.checkCancel();
    if (!promptFits(system,prompt)) throw new FoliException(HttpStatus.BAD_REQUEST,"CONTEXT_LIMIT",
        "This question and its evidence exceed the safe local context budget. Shorten the question or clear the conversation.");
    var health=health();
    if (!"READY".equals(health.get("status"))) throw new FoliException(HttpStatus.SERVICE_UNAVAILABLE,
        health.get("status").toString(), switch (health.get("status").toString()) {
          case "MODEL_MISSING" -> "The configured local model is not installed. Pull it once with Ollama, then retry.";
          case "CLOUD_NOT_DISABLED" -> "Start Ollama with OLLAMA_NO_CLOUD=1. Foli refused to send the question.";
          case "MODEL_SIZE_LIMIT" -> "Choose an installed local model package strictly below 6 GB.";
          default -> "Ollama is offline. Start the local runtime, then retry.";
        });
    long start=System.nanoTime();
    try {
      // Explicit system/user messages. No tool callbacks, advisors, URLs or source paths.
      var response=model.call(new Prompt(List.of(new SystemMessage(system),new UserMessage(prompt)),options(structured)));
      FoliExtractionService.checkCancel();
      String answer=response.getResult().getOutput().getText();
      if (answer==null || answer.isBlank()) throw new FoliException(HttpStatus.BAD_GATEWAY,"EMPTY_REPLY","The local model returned no answer. Retry the question.");
      return new Reply(answer,(System.nanoTime()-start)/1_000_000,
          response.getMetadata().getUsage().getCompletionTokens()==null?0:response.getMetadata().getUsage().getCompletionTokens());
    } catch (FoliException | CancellationException e) { throw e;
    } catch (Exception e) {
      if (Thread.currentThread().isInterrupted()) throw new CancellationException();
      throw new FoliException(HttpStatus.SERVICE_UNAVAILABLE,"MODEL_TIMEOUT_OR_FAILURE",
          "The local model timed out or ran out of resources. Retry with a shorter question, or use the source viewer.");
    }
  }

  public boolean promptFits(String system,String prompt) {
    // The chat API has no truncate=false field in Spring AI 2.0.1. A byte-level
    // upper bound is intentionally conservative for byte-fallback tokenizers.
    // Reserve output and message-template overhead before any request is sent.
    return system.getBytes(java.nio.charset.StandardCharsets.UTF_8).length+
        prompt.getBytes(java.nio.charset.StandardCharsets.UTF_8).length <= config.getContextTokens()-config.getOutputTokens()-512;
  }
}
