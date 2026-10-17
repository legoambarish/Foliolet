package com.sih26190.dms.foli;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.*;
import java.net.http.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.CancellationException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

/** Explicit paid-policy + per-request consent gate. No files, tools, URLs or persistent provider state. */
@Service
public class FoliGeminiModel {
  private final boolean enabled;private final String policy,key,model;
  private final ObjectMapper json=new ObjectMapper();
  private final HttpClient http=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3))
      .followRedirects(HttpClient.Redirect.NEVER).proxy(new ProxySelector(){
        public List<Proxy> select(URI u){return List.of(Proxy.NO_PROXY);}
        public void connectFailed(URI u,SocketAddress a,java.io.IOException e){}
      }).build();
  public FoliGeminiModel(@Value("${foli.gemini.enabled:false}") boolean enabled,
      @Value("${foli.gemini.data-policy:unverified}") String policy,
      @Value("${GEMINI_API_KEY:}") String key,
      @Value("${foli.gemini.model:gemini-3.5-flash-lite}") String model) {
    this.enabled=enabled;this.policy=policy;this.key=key;this.model=model;
    if(!Set.of("gemini-3.5-flash-lite","gemini-3.8-flash","gemini-2.5-flash-lite").contains(model))throw new IllegalArgumentException("Unsupported Gemini model");
  }
  public boolean available(){return enabled && policy.equals("paid-reviewed") && key!=null && !key.isBlank();}
  public FoliLocalModel.Reply ask(boolean consent,String system,String prompt,Object format) {
    // Check BEFORE constructing a request; unknown/unpaid policy always refuses application text.
    if(!consent || !available())throw new FoliException(HttpStatus.FORBIDDEN,"CLOUD_DISABLED","Gemini requires reviewed paid-service handling and explicit consent for this request.");
    if(system.length()+prompt.length()>16000)throw new FoliException(HttpStatus.BAD_REQUEST,"CONTEXT_LIMIT","Cloud excerpt budget exceeded.");
    long start=System.nanoTime();
    try {
      var generation=new LinkedHashMap<String,Object>();generation.put("maxOutputTokens",900);generation.put("temperature",0.1);
      if(format!=null){generation.put("responseMimeType","application/json");if(format instanceof Map<?,?>)generation.put("responseJsonSchema",format);}
      var body=Map.of("systemInstruction",Map.of("parts",List.of(Map.of("text",system))),
          "contents",List.of(Map.of("role","user","parts",List.of(Map.of("text",prompt)))),"generationConfig",generation);
      var request=HttpRequest.newBuilder(URI.create("https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent"))
          .timeout(Duration.ofSeconds(20)).header("x-goog-api-key",key).header("Content-Type","application/json")
          .POST(HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body))).build();
      // A completing body handler keeps the request deadline active through the response body.
      var response=http.send(request,HttpResponse.BodyHandlers.ofByteArray());
      byte[] bytes=response.body();
      if(response.statusCode()!=200 || bytes.length>65536)throw new IllegalStateException();
      var result=json.readTree(bytes);var candidate=result.path("candidates").path(0);
      if(!candidate.path("finishReason").asText().equals("STOP"))throw new IllegalStateException();
      var text=new StringBuilder();for(var part:candidate.path("content").path("parts"))
        if(!part.path("thought").asBoolean(false))text.append(part.path("text").asText());
      if(text.isEmpty())throw new IllegalStateException();
      return new FoliLocalModel.Reply(text.toString(),(System.nanoTime()-start)/1_000_000,result.path("usageMetadata").path("candidatesTokenCount").asLong());
    }catch(InterruptedException e){Thread.currentThread().interrupt();throw new CancellationException();}
    catch(Exception e){throw new FoliException(HttpStatus.SERVICE_UNAVAILABLE,"GEMINI_UNAVAILABLE","Gemini is unavailable, rate limited or returned an unusable response. Local processing remains available.");}
  }
}
