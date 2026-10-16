package com.sih26190.dms.intake;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sih26190.dms.foli.*;
import com.sih26190.dms.selective.*;
import java.util.*;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static com.sih26190.dms.foli.FoliData.*;

class FactSuggestionsTest {
  final ObjectMapper json=new ObjectMapper();
  final FactSuggestions facts=new FactSuggestions(new ClaimCanonicalizer(),new CitationVerifier(),mock(FoliLocalModel.class));
  Snapshot source(String text) {
    var document=new Document("wallet:0x"+"a".repeat(64),"Synthetic marks","synthetic.txt","txt","DRAFT","1",true);
    var page=new Page(1,text,"TEXT",null,1,4,0,List.of(),List.of());
    return new Snapshot(document,PrivateVault.sha256(text.getBytes()),List.of(page),null);
  }
  String reply(String evidence,String label,String type,String value) throws Exception {
    return json.writeValueAsString(Map.of("fields",List.of(Map.of("page",1,"evidence",evidence,"label",label,"type",type,"value",value))));
  }
  @Test void math90HasExactSourceOffsetsAndDeterministicPath() throws Exception {
    var s=source("Name: Synthetic Student\nMath = 90\nScience: 74\n");
    var result=facts.parse(reply("Math = 90","Math","decimal","090.00"),s);
    assertEquals(1,result.fields().size()); var f=result.fields().get(0);
    assertEquals("education.math",f.path()); assertEquals("90",f.value());
    assertEquals("Math = 90",s.pages().get(0).text().substring(f.citation().start(),f.citation().end()));
    assertEquals(s.hash(),f.citation().sourceHash()); assertEquals("1",f.citation().version());
  }
  @Test void numericSubstringsUnitsRangesAndGarbledOcrAreRejected() throws Exception {
    for(String literal:List.of("190","-90","90/100","90-95","9O","O0","90 kg","90 Science: 95","9e1"))
      assertTrue(facts.parse(reply("Math: "+literal,"Math","decimal","90"),source("Math: "+literal)).fields().isEmpty(),literal);
  }
  @Test void numericScoreTypeIsDeterministicAndNumericJsonCannotBypassVerbatimChecks() throws Exception {
    var field=facts.parse(reply("Math: 90","Math","string","90"),source("Math: 90")).fields().get(0);
    assertEquals("decimal",field.type());assertEquals("90",field.value());
    assertEquals("90",facts.parse(reply("Math: 90","Math","decimal","90").replace("\"value\":\"90\"","\"value\":90"),source("Math: 90")).fields().get(0).value());
    assertTrue(facts.parse(reply("Math: 190","Math","decimal","90").replace("\"value\":\"90\"","\"value\":90"),source("Math: 190")).fields().isEmpty());
    assertEquals("string",facts.parse(reply("Product identifier: 00123","Product identifier","string","00123"),source("Product identifier: 00123")).fields().get(0).type());
  }
  @Test void noScoreSwappingOrFabricatedCgpa() throws Exception {
    var s=source("Science: 95\nMath: 90\nCGPA: unavailable\n");
    assertTrue(facts.parse(reply("Math: 90","Science","decimal","90"),s).fields().isEmpty());
    assertTrue(facts.parse(reply("Math: 90","Math","decimal","95"),s).fields().isEmpty());
    assertTrue(facts.parse(reply("CGPA: unavailable","CGPA","decimal","9"),s).fields().isEmpty());
    assertTrue(facts.parse(reply("CGPA: 90","CGPA","decimal","90"),source("CGPA: 90")).fields().isEmpty());
  }
  @Test void evidenceMustBeTheEntirePhysicalLineOnTheNamedPage() throws Exception {
    var s=source("Do not use Math: 90 as a real score\nMath: 95\n");
    assertTrue(facts.parse(reply("Math: 90","Math","decimal","90"),s).fields().isEmpty());
    assertTrue(facts.parse(reply("Math: 95\n","Math","decimal","95"),s).fields().isEmpty());
    assertTrue(facts.parse(reply("Math: 95","Math","decimal","95").replace("\"page\":1","\"page\":9"),s).fields().isEmpty());
  }
  @Test void percentAndGroupingKeepTheirMeaningAndDatesAreStrict() throws Exception {
    var p=facts.parse(reply("Math: 90%","Math","decimal","90"),source("Math: 90%")).fields().get(0);
    assertEquals("Math (%)",p.label()); assertNotEquals("education.math",p.path());
    assertEquals("1234",facts.parse(reply("Total: 1,234","Total","decimal","1234"),source("Total: 1,234")).fields().get(0).value());
    assertTrue(facts.parse(reply("Date: 2026-02-30","Date","date","2026-02-30"),source("Date: 2026-02-30")).fields().isEmpty());
  }
  @Test void lowConfidenceWordsAndAmbiguousColumnsHaveNoAcceptedFacts() throws Exception {
    var nativeSource=source("Math: 90");
    for(var page:List.of(
        new Page(1,"Math: 90","OCR",60d,1,1,0,List.of(),List.of()),
        new Page(1,"Math: 90","OCR",95d,1,1,0,List.of(new Word("90",6,8,0,0,10,10,30)),List.of()),
        new Page(1,"Math: 90","TEXT",null,1,1,0,List.of(),List.of("Multiple columns detected")))) {
      var s=new Snapshot(nativeSource.document(),nativeSource.hash(),List.of(page),null);
      assertTrue(facts.parse(reply("Math: 90","Math","decimal","90"),s).fields().isEmpty());
    }
  }
  @Test void goodOcrRetainsItsTranscriptionWarningAndNoIssuerClaim() throws Exception {
    var s=source("Math: 90");
    var page=new Page(1,"Math: 90","OCR",95d,1,1,90,List.of(new Word("90",6,8,1,2,10,10,96)),List.of("Check OCR against original"));
    var f=facts.parse(reply("Math: 90","Math","decimal","90"),new Snapshot(s.document(),s.hash(),List.of(page),null)).fields().get(0);
    assertEquals("OCR transcription",f.citation().provenance()); assertFalse(f.citation().warnings().isEmpty());
  }
  @Test void mixedPageAcceptsOnlyCorroboratedAdjacentFactsAndChecksTheirOcrWords() throws Exception {
    String text="Math: 90\nScience: 80\n\n[Rendered-page OCR transcription]\nMath: 90\nScience: 8O\n";
    var s=source(text); int at=text.lastIndexOf("90");
    var page=new Page(1,text,"MIXED_OCR",95d,1,7,0,List.of(new Word("90",at,at+2,1,2,10,10,96)),List.of("Embedded text and rendered-page OCR differ"));
    var mixed=new Snapshot(s.document(),s.hash(),List.of(page),null);
    var f=facts.parse(reply("Math: 90","Math","decimal","90"),mixed).fields().get(0);
    assertEquals("Embedded text corroborated by OCR",f.citation().provenance());
    assertTrue(facts.parse(reply("Science: 80","Science","decimal","80"),mixed).fields().isEmpty());
    assertTrue(facts.parse(reply("Science: 8O","Science","string","8O"),mixed).fields().isEmpty());
    var low=new Page(1,text,"MIXED_OCR",95d,1,7,0,List.of(new Word("90",at,at+2,1,2,10,10,20)),List.of());
    assertTrue(facts.parse(reply("Math: 90","Math","decimal","90"),new Snapshot(s.document(),s.hash(),List.of(low),null)).fields().isEmpty());
  }
  @Test void malformedOversizedAndDuplicateProposalsAreBounded() throws Exception {
    assertThrows(IllegalArgumentException.class,() -> facts.parse("broken",source("Math: 90")));
    assertThrows(IllegalArgumentException.class,() -> facts.parse("x".repeat(64001),source("Math: 90")));
    var node=json.readTree(reply("Math: 90","Math","decimal","90")).path("fields").get(0);
    var result=facts.parse(json.writeValueAsString(Map.of("fields",List.of(node,node))),source("Math: 90"));
    assertEquals(1,result.fields().size()); assertEquals(1,result.discarded());
  }
}
