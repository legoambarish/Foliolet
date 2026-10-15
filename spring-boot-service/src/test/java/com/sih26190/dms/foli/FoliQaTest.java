package com.sih26190.dms.foli;

import com.fasterxml.jackson.databind.*;
import com.sih26190.dms.model.Role;
import com.sih26190.dms.repository.UserRepository;
import com.sun.net.httpserver.HttpServer;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import org.junit.jupiter.api.*;
import org.springframework.mock.web.*;
import static com.sih26190.dms.foli.FoliData.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class FoliQaTest {
  final ObjectMapper json=new ObjectMapper();
  final FoliRetrievalService retrieval=new FoliRetrievalService();
  final CitationVerifier verifier=new CitationVerifier();
  Snapshot corpus() throws Exception {
    JsonNode gold=json.readTree(getClass().getResourceAsStream("/foli-gold-cases.json")).path("cases");
    var pages=new ArrayList<Page>();
    for(int i=1;i<=125;i++) {
      String text="Page "+i+". Ordinary operational background information.\n";
      for(var test:gold) if(test.path("kind").asText().equals("document") && test.path("id").asText().startsWith("Q") && test.path("page").asInt()==i)
        text+=test.path("quote").asText()+"\n";
      pages.add(new Page(i,text,"TEXT",null,0,0,0,List.of(),List.of()));
    }
    int chars=pages.stream().mapToInt(p -> p.text().length()).sum();
    return new Snapshot(FoliReadingTest.source(new byte[0],"pdf").document(),"a".repeat(64),pages,
        new Manifest("test","Synthetic","pdf","1","a".repeat(64),"test","test",125,125,125,0,chars,true,List.of(),List.of()));
  }

  @Test void goldRetrievalReportsAllSixtyAnswerableCasesIncludingLatePage() throws Exception {
    var source=corpus(); var missed=new ArrayList<String>(); int checked=0;
    for(var test:json.readTree(getClass().getResourceAsStream("/foli-gold-cases.json")).path("cases")) {
      if(!test.path("kind").asText().equals("document")) continue;
      checked++;
      if(retrieval.retrieve(source,test.path("question").asText()).stream().noneMatch(s -> s.page()==test.path("page").asInt()))
        missed.add(test.path("id").asText());
    }
    System.out.println("Foli gold source-page retrieval: "+(checked-missed.size())+"/"+checked+"; misses="+missed);
    assertTrue(checked-missed.size()>=54,"At least 90% required; misses "+missed);
    assertTrue(retrieval.retrieve(source,"What exception removes the renewal fee?").stream().anyMatch(s -> s.page()==125));
  }
  @Test void verifierRejectsFabricationWrongPageAndWrongOffsets() throws Exception {
    var source=corpus(); var span=retrieval.all(source).get(0);
    var citation=verifier.verify(source,span,null).orElseThrow();
    assertEquals(citation.quote(),source.pages().get(citation.page()-1).text().substring(citation.start(),citation.end()));
    assertTrue(verifier.verify(source,span,"Invented exact quotation").isEmpty());
    assertTrue(verifier.verify(source,new FoliRetrievalService.Span("E9",126,0,5,"wrong"),null).isEmpty());
    assertTrue(verifier.verify(source,new FoliRetrievalService.Span("E9",1,1,span.end(),span.text()),null).isEmpty());
    var warnings=new ArrayList<String>();
    assertTrue(verifier.suppressUnsupportedQuotes("It states \"Invented exact quotation\".",List.of(span),warnings).contains("omitted"));
    assertFalse(warnings.isEmpty());
  }
  @Test void flexibleReadQuestionsReachModelButWriteRequestsHaveNoToolPath() throws Exception {
    var model=mock(FoliLocalModel.class); when(model.promptFits(anyString(),anyString())).thenReturn(true); var service=new FoliChatService(model,retrieval,verifier);
    when(model.ask(anyString(),anyString(),eq(false))).thenReturn(new FoliLocalModel.Reply("A careful-reading haiku.",3,10));
    assertEquals("GENERAL",service.chat("Write a haiku about careful reading",List.of(),null,s -> {}).answerKind());
    assertTrue(service.chat("Delete this document",List.of(),corpus(),s -> {}).answer().contains("cannot"));
    assertTrue(service.chat("Revoke my share link",List.of(),null,s -> {}).answer().contains("cannot"));
    verify(model,times(1)).ask(anyString(),anyString(),anyBoolean());
  }
  @Test void unknownEvidenceAndQuotesAreNotMarkedVerified() throws Exception {
    var model=mock(FoliLocalModel.class); when(model.promptFits(anyString(),anyString())).thenReturn(true); var service=new FoliChatService(model,retrieval,verifier);
    when(model.ask(anyString(),anyString(),eq(true))).thenReturn(new FoliLocalModel.Reply(
        "{\"answer\":\"The fee is \\\"one million\\\" [E9999].\",\"evidence\":[\"E9999\"]}",1,20));
    var result=service.chat("Explain the fee",List.of(),corpus(),s -> {});
    assertTrue(result.citations().isEmpty()); assertEquals("NO_SOURCE_SUPPORT",result.answerKind());
    assertFalse(result.answer().contains("one million")); assertFalse(result.answer().contains("[E9999]"));
  }
  @Test void loopbackOriginRejectsRemoteNamesCredentialsPathsAndRedirectTargets() {
    for(String url:List.of("https://127.0.0.1:11434","http://localhost:11434","http://example.com:11434",
        "http://127.0.0.1:11434/remote","http://u:p@127.0.0.1:11434","http://127.0.0.1:11434?url=https://evil.invalid"))
      assertThrows(IllegalArgumentException.class,() -> FoliLocalModel.localOrigin(url));
    assertEquals("127.0.0.1",FoliLocalModel.localOrigin("http://127.0.0.1:11434").getHost());
  }
  @Test void localTransportRefusesCloudMissingAndOversizedModelsAndUsesNoTools() throws Exception {
    var status=new AtomicReference<>("{\"cloud\":{\"disabled\":true}}");
    var tags=new AtomicReference<>("{\"models\":[{\"name\":\"qwen3:4b-instruct\",\"size\":2497293803}]}");
    var requests=new ArrayList<String>();
    var server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
    server.createContext("/api/status",e -> { byte[] b=status.get().getBytes(); e.sendResponseHeaders(200,b.length); e.getResponseBody().write(b); e.close(); });
    server.createContext("/api/tags",e -> { byte[] b=tags.get().getBytes(); e.sendResponseHeaders(200,b.length); e.getResponseBody().write(b); e.close(); });
    server.createContext("/api/chat",e -> {
      requests.add(new String(e.getRequestBody().readAllBytes(),StandardCharsets.UTF_8));
      byte[] b="{\"model\":\"qwen3:4b-instruct\",\"created_at\":\"2026-10-15T00:00:00Z\",\"message\":{\"role\":\"assistant\",\"content\":\"Local answer\"},\"done\":true,\"eval_count\":2,\"prompt_eval_count\":8}".getBytes();
      e.getResponseHeaders().set("Content-Type","application/json"); e.sendResponseHeaders(200,b.length); e.getResponseBody().write(b); e.close();
    });
    server.start();
    try {
      var config=new FoliProperties(); config.setOllamaUrl("http://127.0.0.1:"+server.getAddress().getPort());
      var model=new FoliLocalModel(config);
      status.set("{\"cloud\":{\"disabled\":false}}");
      assertEquals("CLOUD_NOT_DISABLED",assertThrows(FoliException.class,() -> model.ask("s","p",true)).code());
      status.set("{\"cloud\":{\"disabled\":true}}"); tags.set("{\"models\":[]}");
      assertEquals("MODEL_MISSING",assertThrows(FoliException.class,() -> model.ask("s","p",true)).code());
      tags.set("{\"models\":[{\"name\":\"qwen3:4b-instruct\",\"size\":6000000000}]}");
      assertEquals("MODEL_SIZE_LIMIT",assertThrows(FoliException.class,() -> model.ask("s","p",true)).code());
      assertTrue(requests.isEmpty());
      tags.set("{\"models\":[{\"name\":\"qwen3:4b-instruct\",\"size\":2497293803}]}");
      assertEquals("Local answer",model.ask("s","p",true).text());
      var body=json.readTree(requests.get(0));
      assertTrue(!body.hasNonNull("tools") || body.path("tools").isEmpty()); assertFalse(body.path("stream").asBoolean());
      assertEquals("json",body.path("format").asText());
      assertFalse(model.promptFits("s","x".repeat(8192)));
      assertEquals("CONTEXT_LIMIT",assertThrows(FoliException.class,() -> model.ask("s","x".repeat(8192),true)).code());
    } finally { server.stop(0); }
  }
  @Test void unavailableRuntimeFailsClearly() throws Exception {
    int port; try(var socket=new java.net.ServerSocket(0)) { port=socket.getLocalPort(); }
    var config=new FoliProperties(); config.setOllamaUrl("http://127.0.0.1:"+port);
    assertEquals("OFFLINE",new FoliLocalModel(config).health().get("status"));
  }
  @Test void jobIsolationCancellationAndStaleSource() throws Exception {
    var resolver=mock(AuthorizedDocumentResolver.class); var index=mock(FoliIndex.class); var chat=mock(FoliChatService.class);
    var users=mock(UserRepository.class); var config=new FoliProperties();
    var first=FoliReadingTest.user(1,Role.HOLDER); var second=FoliReadingTest.user(2,Role.ADMIN);
    when(users.findById(1L)).thenReturn(Optional.of(first)); var source=FoliReadingTest.source("source".getBytes(),"txt");
    when(resolver.open(eq("doc"),eq(first))).thenReturn(source);
    var started=new CountDownLatch(1);
    when(index.read(eq("doc"),eq(first),any())).thenAnswer(i -> { started.countDown(); Thread.sleep(60000); return corpus(); });
    try(var closer=new AutoCloseable() { public void close() {} }) {
      var jobs=new FoliJobs(resolver,index,chat,users,config);
      try {
        var job=jobs.create(new FoliJobs.Request("doc","", "index",List.of(),null),first); String id=job.get("id").toString();
        assertTrue(started.await(2,TimeUnit.SECONDS));
        assertEquals(404,assertThrows(FoliException.class,() -> jobs.get(id,second)).getStatusCode().value());
        assertEquals(404,assertThrows(FoliException.class,() -> jobs.stop(id,second)).getStatusCode().value());
        assertEquals("CANCELLED",jobs.stop(id,first).get("state"));
        when(resolver.open(eq("doc"),eq(first))).thenReturn(new Source(source.document(),"b".repeat(64),source.bytes()));
        assertEquals("SOURCE_CHANGED",assertThrows(FoliException.class,() -> jobs.get(id,first)).code());
        verifyNoInteractions(chat);
      } finally { jobs.close(); }
    }
  }
  @Test void privateBoundaryRejectsOriginsRemoteRequestsAndOversizedBodies() throws Exception {
    var filter=new FoliBoundaryFilter(new FoliProperties());
    for(String scenario:List.of("remote","origin","header","size")) {
      var request=new MockHttpServletRequest("POST","/api/foli/jobs"); request.setRemoteAddr("127.0.0.1");
      request.setContentType("application/json"); request.addHeader("X-Foli-Client","private"); request.setContent("{}".getBytes());
      if(scenario.equals("remote")) request.setRemoteAddr("203.0.113.5");
      if(scenario.equals("origin")) request.addHeader("Origin","https://evil.invalid");
      if(scenario.equals("header")) request.removeHeader("X-Foli-Client");
      if(scenario.equals("size")) request.setContent(new byte[32770]);
      var response=new MockHttpServletResponse(); var reached=new AtomicBoolean();
      filter.doFilter(request,response,(q,s) -> reached.set(true));
      assertFalse(reached.get(),scenario); assertTrue(response.getStatus()>=400); assertTrue(response.getHeader("Cache-Control").contains("no-store"));
    }
  }
}
