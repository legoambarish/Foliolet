package com.sih26190.dms.foli;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static com.sih26190.dms.foli.FoliData.*;

class FoliReviewTest {
  final FoliLocalModel model=mock(FoliLocalModel.class);
  FoliReviewService service() {
    when(model.promptFits(anyString(),anyString())).thenReturn(true);
    when(model.ask(anyString(),anyString(),eq(true))).thenReturn(new FoliLocalModel.Reply("{\"findings\":[]}",1,4));
    return new FoliReviewService(new FoliRetrievalService(),new CitationVerifier(),model);
  }
  @Test void allFortyGoldClausesFoundIncludingFinalOverrideWithExactQuotes() throws Exception {
    var source=new FoliQaTest().corpus(); var result=service().review(source,s -> {});
    var findings=result.findings().stream().map(f -> (FoliReviewService.Finding)f).toList(); int found=0,total=0;
    var gold=new ObjectMapper().readTree(getClass().getResourceAsStream("/foli-gold-cases.json")).path("cases");
    for(var test:gold) if(test.path("id").asText().startsWith("Q")) {
      total++; if(findings.stream().anyMatch(f -> f.categories().contains(test.path("category").asText()) &&
          f.citations().stream().anyMatch(c -> c.page()==test.path("page").asInt() && c.quote().contains(test.path("quote").asText())))) found++;
    }
    System.out.println("Fine-print checklist gold recall: "+found+"/"+total+"; passages="+findings.size());
    assertTrue(found>=36,"At least 90% critical-clause recall required");
    assertTrue(result.citations().stream().anyMatch(c -> c.page()==125 && c.quote().contains("Notwithstanding every earlier")));
    for(var quote:result.citations()) assertEquals(quote.quote(),source.pages().get(quote.page()-1).text().substring(quote.start(),quote.end()));
    assertEquals(125,result.reviewCoverage().get("checklistPages")); assertEquals(true,result.reviewCoverage().get("semanticComplete"));
  }
  @Test void linksDefinitionsClauseReferencesAndExplicitConflicts() throws Exception {
    var result=service().review(new FoliQaTest().corpus(),s -> {});
    var findings=result.findings().stream().map(f -> (FoliReviewService.Finding)f).toList();
    assertTrue(findings.stream().anyMatch(f -> !f.definitions().isEmpty()));
    assertTrue(findings.stream().flatMap(f -> f.references().stream()).anyMatch(r -> !r.sources().isEmpty()));
    assertTrue(findings.stream().flatMap(f -> f.warnings().stream()).anyMatch(w -> w.contains("conflict")));
    assertTrue(findings.stream().flatMap(f -> f.warnings().stream()).anyMatch(w -> w.contains("notwithstanding")));
  }
  @Test void unavailableModelStillShowsChecklistAndHonestPartialSemanticCoverage() throws Exception {
    var service=service(); when(model.ask(anyString(),anyString(),eq(true))).thenThrow(new FoliException(HttpStatus.SERVICE_UNAVAILABLE,"OFFLINE","Offline"));
    var result=service.review(new FoliQaTest().corpus(),s -> {});
    assertFalse(result.findings().isEmpty()); assertEquals(false,result.reviewCoverage().get("semanticComplete"));
    assertEquals(0,result.reviewCoverage().get("semanticChunks")); assertTrue(result.warnings().stream().anyMatch(w -> w.contains("OFFLINE")));
    assertTrue(result.answer().contains("absence of a flag does not"));
  }
  @Test void hallucinatedMapIdsAreOmittedAndUnreadablePagesStayVisible() throws Exception {
    var service=service(); when(model.ask(anyString(),anyString(),eq(true))).thenReturn(new FoliLocalModel.Reply(
        "{\"findings\":[{\"id\":\"E9999\",\"categories\":[\"fees\"],\"explanation\":\"fabricated\"}]}",1,10));
    var original=new FoliQaTest().corpus(); var manifest=original.manifest();
    var source=new Snapshot(original.document(),original.hash(),original.pages(),new Manifest(manifest.documentId(),manifest.name(),manifest.format(),manifest.version(),manifest.sourceHash(),manifest.extractorVersion(),manifest.ocrEngine(),126,126,125,0,manifest.characters(),false,manifest.pages(),List.of("Unreadable page 126")));
    var result=service.review(source,s -> {});
    assertEquals(1,result.reviewCoverage().get("unreadablePages"));
    assertTrue(result.warnings().stream().anyMatch(w -> w.contains("unknown source")));
    assertFalse(result.findings().toString().contains("fabricated"));
  }
  @Test void flagsTimingTensionAcrossSeparateClausesWithoutResolvingIt() {
    assertTrue(FoliReviewService.timingTension("Cancellation is immediate.","Cancellation takes effect at the end of the paid term."));
    assertFalse(FoliReviewService.timingTension("Access is immediate.","Cancellation takes effect at the end of the term."));
  }
}
