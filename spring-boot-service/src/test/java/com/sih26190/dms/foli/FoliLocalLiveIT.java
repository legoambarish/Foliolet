package com.sih26190.dms.foli;

import java.net.Socket;
import java.security.Permission;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Explicit live gate; the temporary Java 17 network guard is test-only. */
@SuppressWarnings("removal")
class FoliLocalLiveIT {
  @Test void realOllamaInferenceWithNonLoopbackJavaNetworkingDenied() throws Exception {
    var config=new FoliProperties(); config.setOutputTokens(180);
    config.setOllamaUrl(System.getenv().getOrDefault("FOLI_OLLAMA_URL",config.getOllamaUrl()));
    var model=new FoliLocalModel(config);
    assertEquals("READY",model.health().get("status"),"Start the documented local cloud-disabled runtime first");
    SecurityManager previous=System.getSecurityManager(); var denied=new AtomicInteger();
    var guard=new SecurityManager() {
      @Override public void checkPermission(Permission permission) {}
      @Override public void checkPermission(Permission permission,Object context) {}
      @Override public void checkConnect(String host,int port) {
        if(!Set.of("127.0.0.1","::1","[::1]","0:0:0:0:0:0:0:1").contains(host)) {
          denied.incrementAndGet(); throw new SecurityException("Non-loopback networking denied in live offline gate");
        }
      }
    };
    try {
      System.setSecurityManager(guard);
      assertThrows(SecurityException.class,() -> { try(var ignored=new Socket("example.com",443)) {} });
      int controls=denied.get();
      assertDoesNotThrow(() -> model.get("/api/status"));
      var answer=model.ask(FoliChatService.SYSTEM,"Source: The dormant-account fee is INR 9300. Question: What is the fee? Answer briefly.",false);
      assertTrue(answer.text().contains("9300")); assertEquals(controls,denied.get(),"Inference attempted non-loopback Java networking");
      System.out.println("Live local inference with Java external networking denied: "+answer.milliseconds()+"ms, "+answer.outputTokens()+" tokens. Ollama cloud-disabled status was verified.");
    } finally { System.setSecurityManager(previous); }
  }
}
