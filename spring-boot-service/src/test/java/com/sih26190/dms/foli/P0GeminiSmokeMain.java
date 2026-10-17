package com.sih26190.dms.foli;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;

/** Transport smoke test: hardcoded fictional text only; no application/user/file input.
 * The test fixture supplies the policy gate, NOT an attestation about the real account.
 * Never enable paid-reviewed in the running application from this experiment.
 */
public final class P0GeminiSmokeMain {
  public static void main(String[] args) throws Exception {
    var config=new FoliProperties();config.setOllamaUrl("http://127.0.0.1:11444");
    var model=new FoliLocalModel(config);
    var cloud=new FoliGeminiModel(true,"paid-reviewed",System.getenv("GEMINI_API_KEY"),"gemini-3.5-flash-lite");
    var service=new FoliChatService(model,new FoliRetrievalService(),new CitationVerifier(),cloud);
    var source=new FoliExtractionService(config,new OcrService(config)).extract(FoliReadingTest.source(
        "FICTIONAL BENCHMARK. A dormant account fee is INR 9300 after 90 days unless timely cancellation applies. Written cancellation within 7 days waives the fee.".getBytes(StandardCharsets.UTF_8),"txt"),s->{});
    var rows=new ArrayList<Map<String,Object>>();
    for(boolean document:List.of(false,true)) {
      long start=System.nanoTime();
      var answer=service.chat(document?"What is the fee and its cancellation exception?":"Explain selective disclosure in two sentences.",List.of(),document?source:null,s->{},true);
      if(answer.warnings().stream().noneMatch(w->w.startsWith("Gemini received")))throw new IllegalStateException("Cloud transport did not complete; local fallback is not a cloud success");
      if(document && answer.citations().isEmpty())throw new IllegalStateException("Missing validated citation");
      rows.add(Map.of("document",document,"totalMs",(System.nanoTime()-start)/1_000_000,"result",answer));
    }
    new com.fasterxml.jackson.databind.ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(Path.of(args[0]).toFile(),
        Map.of("fictionalOnly",true,"billingTier","UNVERIFIED","applicationCloudEnabled",false,"cases",rows));
    System.out.println("PASS actual Gemini adapter and grounded citation validation on fixed fictional text only");
  }
}
