package com.sih26190.dms.intake;

import com.sih26190.dms.foli.*;
import com.sih26190.dms.selective.*;
import java.io.*;
import java.util.*;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.font.*;
import org.junit.jupiter.api.*;
import static com.sih26190.dms.foli.FoliData.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class LayoutFactsTest {
  final FoliLocalModel model=mock(FoliLocalModel.class);
  final FactSuggestions facts=new FactSuggestions(new ClaimCanonicalizer(),new CitationVerifier(),model);
  final PDType1Font font=new PDType1Font(Standard14Fonts.FontName.HELVETICA);
  void text(PDPageContentStream c,float x,float y,String value)throws Exception{c.beginText();c.setFont(font,11);c.newLineAtOffset(x,y);c.showText(value);c.endText();}
  Snapshot pdf(boolean duplicate,boolean hidden)throws Exception {
    byte[] data;
    try(var d=new PDDocument()) {
      var p=new PDPage();d.addPage(p);
      try(var c=new PDPageContentStream(d,p)) {
        text(c,40,740,"Student Name");text(c,210,740,"Fictional Student");
        text(c,40,710,"CGPA");text(c,210,710,"8.67");
        text(c,40,650,"Subject");text(c,280,650,"Max Marks");text(c,390,650,"Marks Obtained");text(c,520,650,"Grade");
        text(c,40,620,"Mathematics");text(c,280,620,"100");text(c,390,620,"91");text(c,520,620,"A+");
        text(c,40,590,"Physics");text(c,280,590,"100");text(c,390,590,"86");text(c,520,590,"A");
        if(duplicate)text(c,390,620,"71");
        if(hidden){c.setRenderingMode(org.apache.pdfbox.pdmodel.graphics.state.RenderingMode.NEITHER);text(c,40,540,"Science: 99");}
      }
      var out=new ByteArrayOutputStream();d.save(out);data=out.toByteArray();
    }
    var cfg=new FoliProperties();cfg.setTesseract("missing-test-executable");
    var ocr=mock(OcrService.class);when(ocr.recognizeLayout(any())).thenReturn(List.of(new OcrService.Result("",0,0,List.of(),"OCR unavailable")));
    var doc=new Document("wallet:0x"+"a".repeat(64),"Fictional table","table.pdf","pdf","DRAFT","1",true);
    return new FoliExtractionService(cfg,ocr).extract(new Source(doc,PrivateVault.sha256(data),data),ignored -> {});
  }
  FactSuggestions.Result suggest(Snapshot s){return facts.suggest(s,ignored -> {});}
  @Test void pdfBoxTableAndAdjacentCellsProduceExactLocationsDespiteColumnWarning()throws Exception {
    var s=pdf(false,false);assertTrue(s.pages().get(0).warnings().stream().anyMatch(w -> w.contains("columns")));
    var r=suggest(s);assertEquals(8,r.fields().size());assertEquals(8,r.diagnostics().get("supported"));
    assertEquals("91",r.fields().stream().filter(f -> f.path().equals("education.math")).findFirst().orElseThrow().value());
    assertEquals("8.67",r.fields().stream().filter(f -> f.path().equals("education.cgpa")).findFirst().orElseThrow().value());
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Physics marks") && f.value().equals("86")));
    for(var f:r.fields()) {
      assertEquals(s.hash(),f.citation().sourceHash());var all=new ArrayList<FactSuggestions.Fragment>();all.addAll(f.support().labels());all.addAll(f.support().values());all.addAll(f.support().headers());
      for(var part:all){assertEquals(part.quote(),s.pages().get(0).text().substring(part.start(),part.end()));assertTrue(part.left()>=0 && part.left()+part.width()<=1.01);}
      if(f.support().relationship().equals("TABLE_HEADER_AND_ROW"))assertFalse(f.support().headers().isEmpty());
    }
    verifyNoInteractions(model);
  }
  @Test void overlappingNumericCellsCannotBecomeSupportedMarks()throws Exception {
    var r=suggest(pdf(true,false));
    assertFalse(r.fields().stream().anyMatch(f -> f.path().equals("education.math") && f.support().quality().equals("SUPPORTED")));
    assertFalse(r.fields().stream().anyMatch(f -> f.path().equals("education.math")),"Overprinted numeric glyphs must not become a concatenated mark");
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Physics marks") && f.value().equals("86")));
  }
  @Test void invisiblePdfTextIsWithheldWithoutRejectingOtherFields()throws Exception {
    var r=suggest(pdf(false,true));assertFalse(r.fields().stream().anyMatch(f -> f.label().equals("Science")));
    assertTrue(((Map<?,?>)r.diagnostics().get("rejections")).containsKey("INVISIBLE_SOURCE_TEXT"));
    assertTrue(r.fields().stream().anyMatch(f -> f.path().equals("person.name")));
    assertTrue(r.fields().stream().allMatch(f -> f.support().quality().equals("REVIEW_REQUIRED")),"Missing rendered-page check cannot silently promote suspicious native text");
  }
  Snapshot ocr(String primary,String check,double valueConfidence,boolean unrelatedNoise) {
    String text="Math: "+primary+"\n"+(unrelatedNoise?"noise\n":"")+"[check]\nMath: "+check;
    int a=text.lastIndexOf("Math"),v=text.lastIndexOf(check);
    var w=new ArrayList<>(List.of(new Word("Math:",0,5,20,20,50,20,96),new Word(primary,6,6+primary.length(),90,20,30,20,valueConfidence)));
    if(unrelatedNoise)w.add(new Word("noise",9,14,20,220,40,20,2));
    var layers=List.of(new Layer("ocr","OCR",0,600,800,w,List.of()),new Layer("check","OCR_CHECK",0,600,800,List.of(new Word("Math:",a,a+5,20,20,50,20,96),new Word(check,v,v+check.length(),90,20,30,20,valueConfidence)),List.of()));
    var page=new Page(1,text,"OCR",94d,0,0,0,w,List.of("OCR"),layers);
    var doc=new Document("wallet:0x"+"b".repeat(64),"Fictional OCR","scan.pdf","pdf","DRAFT","1",true);
    return new Snapshot(doc,"b".repeat(64),List.of(page),null);
  }
  @Test void confidentlyWrongOcrNumberIsNeverPromotedAndDisagreementIsRetained() {
    var r=suggest(ocr("71","91",99,false));assertEquals(1,r.fields().size());var f=r.fields().get(0);
    assertEquals("REVIEW_REQUIRED",f.support().quality());assertTrue(f.support().reasons().contains("CONFLICTING_READINGS"));assertFalse(f.support().alternatives().isEmpty());
    assertEquals("71",f.value());assertEquals(0,r.diagnostics().get("supported"));
  }
  @Test void lowConfidenceValueIsWithheldEvenWithHighPageConfidence() {
    var r=suggest(ocr("71","71",12,false));assertTrue(r.fields().isEmpty());
    assertTrue(((Map<?,?>)r.diagnostics().get("rejections")).containsKey("OCR_TOO_WEAK_TO_SUGGEST"));
  }
  @Test void unrelatedLowConfidenceNoiseDoesNotRejectAnOtherwiseAlignedOcrField() {
    var r=suggest(ocr("91","91",96,true));assertEquals(1,r.fields().size());
    assertEquals("REVIEW_REQUIRED",r.fields().get(0).support().quality());
    assertFalse(r.fields().get(0).support().reasons().contains("LOW_FIELD_OCR_CONFIDENCE"));
  }
  @Test void garbledNumericTextIsKeptForReviewWithoutLetterToDigitRepair() {
    var r=suggest(ocr("9O","9O",96,false));assertEquals("9O",r.fields().get(0).value());assertEquals("string",r.fields().get(0).type());
    assertTrue(r.fields().get(0).support().reasons().contains("OCR_CHARACTER_CONFUSION"));
  }
  @Test void sourceOffsetTamperingCannotYieldAField() {
    var s=ocr("91","91",96,false);var p=s.pages().get(0);var original=p.layers().get(0);
    var broken=new Layer("broken","OCR",0,600,800,List.of(new Word("Math:",1,6,20,20,50,20,96),new Word("91",7,9,90,20,30,20,96)),List.of());
    var page=new Page(1,p.text(),p.status(),p.confidence(),0,0,0,List.of(),List.of(),List.of(broken));
    var r=suggest(new Snapshot(s.document(),s.hash(),List.of(page),null));assertTrue(r.fields().isEmpty());
    assertEquals(2,((Map<?,?>)r.diagnostics().get("rejections")).get("WORD_OFFSET_OR_GEOMETRY_MISMATCH"));
  }
  @Test void literalDatesAndLeadingZeroIdentifiersAreNotGuessed() {
    String text="Date of Birth: 14 July 2004\nEnrollment Number: 001234\nIssue Date: 01/02/2026\nCGPA: unavailable\n";
    var doc=new Document("wallet:0x"+"c".repeat(64),"Fictional text","source.txt","txt","DRAFT","1",true);
    var r=suggest(new Snapshot(doc,"c".repeat(64),List.of(new Page(1,text,"TEXT",null,1,4,0,List.of(),List.of())),null));
    assertTrue(r.fields().stream().anyMatch(f -> f.path().equals("person.birth_date") && f.value().equals("2004-07-14") && f.support().normalization().equals("EXPLICIT_MONTH_NAME")));
    assertTrue(r.fields().stream().anyMatch(f -> f.value().equals("001234") && f.type().equals("string")));
    assertTrue(r.fields().stream().anyMatch(f -> f.value().equals("01/02/2026") && f.support().quality().equals("REVIEW_REQUIRED")));
    assertFalse(r.fields().stream().anyMatch(f -> f.path().equals("education.cgpa")));
  }
  Snapshot unusualCells() {
    String text="Award Code NV001";var words=List.of(new Word("Award",0,5,20,20,40,18,100),new Word("Code",6,10,65,20,35,18,100),new Word("NV001",11,16,220,20,50,18,100));
    var layer=new Layer("native","NATIVE",0,600,800,words,List.of());
    return new Snapshot(new Document("wallet:0x"+"d".repeat(64),"Unusual cells","cells.pdf","pdf","DRAFT","1",true),"d".repeat(64),
        List.of(new Page(1,text,"TEXT",null,0,0,0,List.of(),List.of(),List.of(layer))),null);
  }
  @Test void localModelCanOnlyLinkExistingCellsAndCannotSupplyItsOwnValue() {
    when(model.ask(anyString(),anyString(),anyMap())).thenReturn(new FoliLocalModel.Reply("{\"pairs\":[{\"labelCell\":\"P1_native_R0_C0\",\"valueCell\":\"P1_native_R0_C1\",\"value\":\"FORGED\"}]}",1,1));
    var r=suggest(unusualCells());assertEquals(1,r.fields().size());assertEquals("NV001",r.fields().get(0).value());
    assertEquals("REVIEW_REQUIRED",r.fields().get(0).support().quality());assertEquals(1,r.diagnostics().get("modelCalls"));
  }
  @Test void unknownModelReferencesNeverBecomeSuggestions() {
    when(model.ask(anyString(),anyString(),anyMap())).thenReturn(new FoliLocalModel.Reply("{\"pairs\":[{\"labelCell\":\"P9_native_R0_C0\",\"valueCell\":\"P1_native_R0_C1\"}]}",1,1));
    var r=suggest(unusualCells());assertTrue(r.fields().isEmpty());assertEquals(1,((Map<?,?>)r.diagnostics().get("rejections")).get("MODEL_UNKNOWN_CELL"));
  }
  @Test void offlineLinkerDoesNotRemoveOriginalOrPretendSourceChecksFailed() {
    when(model.ask(anyString(),anyString(),anyMap())).thenThrow(new FoliException(org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE,"OFFLINE","offline"));
    var r=suggest(unusualCells());assertTrue(r.fields().isEmpty());assertEquals("OFFLINE",r.diagnostics().get("modelStatus"));
  }
  @Test void exactDobAnchorDoesNotAcquireUnrelatedBilingualLabelNoise() {
    var s=ocr("14/07/2004","14/07/2004",97,false);String text="unreadable /DOB: 14/07/2004";
    var words=List.of(new Word("unreadable",0,10,10,20,70,20,10),new Word("/DOB:",11,16,85,20,55,20,96),new Word("14/07/2004",17,27,145,20,100,20,97));
    var page=new Page(1,text,"OCR",80d,0,0,0,words,List.of(),List.of(new Layer("ocr","OCR",0,600,800,words,List.of())));
    assertEquals(text.length(),27);
    var r=suggest(new Snapshot(s.document(),s.hash(),List.of(page),null));
    assertEquals(1,r.fields().size());assertEquals("person.birth_date",r.fields().get(0).path());assertEquals("2004-07-14",r.fields().get(0).value());
    assertTrue(r.fields().get(0).support().labels().stream().allMatch(f -> !f.quote().contains("unreadable")));
  }
  @Test void aMergedNameAndValueRequiresReviewInsteadOfRejectingTheField() {
    var s=unusualCells();String text="Name Fictional Student";var words=List.of(new Word(text,0,text.length(),20,20,210,20,100));
    var page=new Page(1,text,"TEXT",null,0,0,0,List.of(),List.of(),List.of(new Layer("native","NATIVE",0,600,800,words,List.of())));
    var r=suggest(new Snapshot(s.document(),s.hash(),List.of(page),null));assertEquals("Fictional Student",r.fields().get(0).value());assertEquals("REVIEW_REQUIRED",r.fields().get(0).support().quality());
  }
  @Test void centredPluralSubjectHeaderAndMaximumNoteRetainTotalMarksMeaning() throws Exception {
    byte[] data;
    try(var pdf=new PDDocument();var out=new ByteArrayOutputStream()) {
      var page=new PDPage();pdf.addPage(page);
      try(var c=new PDPageContentStream(pdf,page)) {
        text(c,180,700,"SUBJECTS");text(c,360,700,"TOTAL MARKS");
        text(c,360,678,"Max. Marks:100");
        text(c,60,645,"Mathematics");text(c,375,645,"091");
        text(c,80,610,"Physics");text(c,375,610,"086");
      }
      pdf.save(out);data=out.toByteArray();
    }
    var cfg=new FoliProperties();var doc=unusualCells().document();
    var r=suggest(new FoliExtractionService(cfg,mock(OcrService.class)).extract(new Source(doc,PrivateVault.sha256(data),data),x -> {}));
    assertEquals(2,r.fields().size());assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Mathematics total marks") && f.value().equals("91")));
    assertTrue(r.fields().stream().allMatch(f -> f.support().headers().stream().anyMatch(h -> h.quote().contains("Max."))));
  }
  Snapshot positioned(String[][] rows) {
    var text=new StringBuilder();var words=new ArrayList<Word>();
    for(var row:rows) {
      int start=text.length();text.append(row[2]).append('\n');
      words.add(new Word(row[2],start,start+row[2].length(),Integer.parseInt(row[0]),Integer.parseInt(row[1]),Math.max(8,row[2].length()*5),10,100));
    }
    var layer=new Layer("native","NATIVE",0,1000,1000,words,List.of());
    return new Snapshot(unusualCells().document(),"e".repeat(64),List.of(new Page(1,text.toString(),"TEXT",null,0,0,0,List.of(),List.of(),List.of(layer))),null);
  }
  @Test void separateColonIsSkippedAndBilingualEnglishAnchorRetainsExactEvidence() {
    var r=suggest(positioned(new String[][]{{"30","20","Name"},{"160","20",":"},{"220","20","MIRA EXAMPLE"},
        {"30","60","ifj.kke RESULT: PASS"},{"30","100","noise Mother's Name"},{"220","100","LEELA EXAMPLE"}}));
    assertEquals(3,r.fields().size());
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Name") && f.value().equals("MIRA EXAMPLE")));
    var result=r.fields().stream().filter(f -> f.label().equals("RESULT")).findFirst().orElseThrow();
    assertEquals("PASS",result.value());assertEquals("RESULT",result.support().labels().get(0).quote());
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Mother's Name") && f.value().equals("LEELA EXAMPLE")));
    verifyNoInteractions(model);
  }
  @Test void headersSubjectListsAndProseDoNotBecomeHolderFacts() {
    var r=suggest(positioned(new String[][]{{"30","20","TOTAL"},{"220","20","TOTAL (IN WORDS)"},
        {"30","60","RESULT: EDUCATION COMPUTER CHEMISTRY MATHEMATICS"},
        {"30","100","NAME EDUCATIONAL Father's/Guardian's This"},{"30","140","Result: PASS"}}));
    assertEquals(1,r.fields().size());assertEquals("PASS",r.fields().get(0).value());
    assertTrue(((Map<?,?>)r.diagnostics().get("rejections")).containsKey("LABEL_VALUE_SEMANTIC_MISMATCH"));
    verifyNoInteractions(model);
  }
  @Test void resultDateDoesNotLoseItsDateLabelToTheResultAnchor() {
    var r=suggest(positioned(new String[][]{{"30","20","Date of declaration of result: 19/06/2024"}}));
    assertEquals(1,r.fields().size());assertEquals("Date of declaration of result",r.fields().get(0).label());
    assertEquals("2024-06-19",r.fields().get(0).value());assertEquals("date",r.fields().get(0).type());
  }
  @Test void multiLineTableCaptionsKeepTotalSeparateFromWordsAndGrade() {
    var r=suggest(positioned(new String[][]{{"20","20","SUBJECT"},{"170","20","SUBJECT NAME"},{"360","20","THEORY"},
        {"480","20","PRACTICAL"},{"610","20","TOTAL"},{"720","20","TOTAL (IN WORDS)"},{"900","20","POSITIONAL"},
        {"20","35","CODE"},{"900","35","GRADE"},
        {"20","65","041"},{"170","65","MATHEMATICS"},{"360","65","051"},{"480","65","026"},
        {"610","65","077"},{"720","65","SEVENTY SEVEN"},{"900","65","B1"},
        {"20","90","502"},{"170","90","HEALTH & PHYSICAL"},{"610","90","---"},{"900","90","A2"},
        {"170","105","EDUCATION"},
        {"20","130","503"},{"170","130","GENERAL STUDIES"},{"610","130","---"},{"900","130","A2"}}));
    assertEquals(6,r.fields().size());
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("MATHEMATICS total marks") && f.value().equals("77")));
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("MATHEMATICS grade") && f.value().equals("B1")));
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("HEALTH & PHYSICAL EDUCATION grade")));
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("GENERAL STUDIES grade")));
    assertTrue(r.fields().stream().allMatch(f -> f.support().relationship().equals("TABLE_HEADER_AND_ROW")));
    verifyNoInteractions(model);
  }
  @Test void percentageMarksColumnKeepsOnlyItsPrintedNumericToken() {
    var r=suggest(positioned(new String[][]{{"30","20","Subjects"},{"400","20","Percentage Marks"},{"800","20","Grade"},
        {"30","60","MATHEMATICS"},{"400","60","87 EIGHT SEVEN"},{"800","60","2 TWO"}}));
    var f=r.fields().stream().filter(c -> c.path().equals("education.math")).findFirst().orElseThrow();
    assertEquals("87",f.value());assertEquals("87",f.support().values().get(0).quote());
    assertEquals(2,r.fields().size());verifyNoInteractions(model);
  }
  @Test void assessmentSectionIsNotAppendedToThePreviousSubject() {
    var r=suggest(positioned(new String[][]{{"30","20","Subjects"},{"400","20","Percentage Marks"},{"800","20","Grade"},
        {"30","60","COMPUTER SCIENCE"},{"400","60","87 EIGHT SEVEN"},{"800","60","2 TWO"},
        {"30","85","INTERNAL ASSESSMENT"},{"30","110","COMMUNITY SERVICE"},{"800","110","A"}}));
    assertEquals(2,r.fields().size());assertTrue(r.fields().stream().allMatch(f -> f.label().startsWith("COMPUTER SCIENCE ")));
    assertTrue(r.fields().stream().noneMatch(f -> f.label().contains("ASSESSMENT")));
  }
  @Test void unknownExplicitOcrLabelsAreRetainedWithoutInventingCharacters() {
    var source=positioned(new String[][]{{"30","20","Policy Number: 0000719"},{"30","60","Blood Group: O+"},
        {"30","100","Invoice Reference:"},{"400","100","INV-0042"},{"30","140","नाम: मीरा"}});
    var p=source.pages().get(0);var l=p.layers().get(0);
    var scan=new Page(1,p.text(),"OCR",99d,0,0,0,l.words(),List.of(),List.of(new Layer("ocr","OCR",0,l.width(),l.height(),l.words(),List.of())));
    var r=suggest(new Snapshot(source.document(),source.hash(),List.of(scan),null));
    assertEquals(4,r.fields().size());assertTrue(r.fields().stream().allMatch(f -> f.support().quality().equals("REVIEW_REQUIRED")));
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Policy Number") && f.value().equals("0000719") && f.type().equals("string")));
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("नाम") && f.value().equals("मीरा")));
    verifyNoInteractions(model);
  }
  @Test void partialStructuredSuccessStillLinksOnlyTheUnresolvedPair() {
    when(model.ask(anyString(),anyString(),anyMap())).thenAnswer(call -> {
      String prompt=call.getArgument(1);assertFalse(prompt.contains("MIRA"));assertFalse(prompt.contains("Result"));
      return new FoliLocalModel.Reply("{\"pairs\":[{\"labelCell\":\"P1_native_R1_C0\",\"valueCell\":\"P1_native_R1_C1\"}]}",1,1);
    });
    var r=suggest(positioned(new String[][]{{"30","20","Name: MIRA EXAMPLE"},{"30","60","Award Code"},{"400","60","NV001"},
        {"30","100","Result: PASS"}}));
    assertEquals(3,r.fields().size());assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Award Code") && f.value().equals("NV001")));
    verify(model,times(1)).ask(anyString(),anyString(),anyMap());
  }
  @Test void rightAlignedTableValuesDoNotMoveIntoTheNextColumn() {
    var r=suggest(positioned(new String[][]{{"30","20","Subject"},{"300","20","Max Marks"},{"400","20","Marks Obtained"},{"600","20","Grade"},
        {"30","60","Physics"},{"370","60","100"},{"560","60","086"},{"620","60","A2"}}));
    assertEquals(3,r.fields().size());
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Physics maximum marks") && f.value().equals("100")));
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Physics marks") && f.value().equals("86")));
    verifyNoInteractions(model);
  }
  @Test void meaningfulLabelPrefixesAndLongOrUnicodePathsRemainDistinct() {
    var r=suggest(positioned(new String[][]{{"30","20","Previous School: North Valley"},{"30","60","School: South Valley"}}));
    assertEquals(2,r.fields().size());assertTrue(r.fields().stream().noneMatch(f -> f.support().reasons().contains("CONFLICTING_READINGS")));
    assertNotEquals(FactSuggestions.path("नाम"),FactSuggestions.path("पता"));
    assertNotEquals(FactSuggestions.path("a".repeat(65)+" x"),FactSuggestions.path("a".repeat(65)+" y"));
  }
  @Test void fullWalletCapacityIsExtractedAndOverflowIsExplicit() {
    var text=new StringBuilder();for(int i=1;i<=70;i++)text.append("Custom field ").append(i).append(": value ").append(i).append('\n');
    var doc=new Document("wallet:0x"+"c".repeat(64),"Fields","source.txt","txt","DRAFT","1",true);
    var r=suggest(new Snapshot(doc,"c".repeat(64),List.of(new Page(1,text.toString(),"TEXT",null,1,70,0,List.of(),List.of())),null));
    assertEquals(64,r.fields().size());assertTrue(r.partial());assertEquals(6,((Map<?,?>)r.diagnostics().get("rejections")).get("FIELD_COUNT_LIMIT"));
    assertTrue(r.warnings().stream().anyMatch(w -> w.contains("64 facts")));verifyNoInteractions(model);
  }
  @Test void unfamiliarSeparatedDelimitersAndPrintedAbsentMarksAreNotLost() {
    var r=suggest(positioned(new String[][]{{"30","20","Policy Number"},{"300","20",":"},{"400","20","000123"},
        {"30","80","Subject"},{"400","80","Marks Obtained"},{"30","120","Physics"},{"400","120","AB"}}));
    assertEquals(2,r.fields().size());
    assertTrue(r.fields().stream().anyMatch(f -> f.label().equals("Policy Number") && f.value().equals("000123")));
    var absent=r.fields().stream().filter(f -> f.label().equals("Physics marks")).findFirst().orElseThrow();
    assertEquals("AB",absent.value());assertEquals("string",absent.type());assertEquals("REVIEW_REQUIRED",absent.support().quality());
    verifyNoInteractions(model);
  }
  @Test void discardedOrientationsAndWeakOrphanCellsDoNotTriggerSlowModelCalls() {
    var s=ocr("91","91",99,false);var p=s.pages().get(0);
    String extra="\nAward Code NV001";int at=p.text().length()+1;
    var bad=new Layer("wrong-direction","OCR_CHECK",90,600,800,List.of(
        new Word("Award Code",at,at+10,20,300,80,18,99),new Word("NV001",at+11,at+16,220,300,50,18,99)),List.of());
    var layers=new ArrayList<>(p.layers());layers.add(bad);
    var page=new Page(1,p.text()+extra,p.status(),p.confidence(),0,0,0,p.words(),List.of(),layers);
    var r=suggest(new Snapshot(s.document(),s.hash(),List.of(page),null));
    assertEquals(1,r.fields().size());assertEquals("91",r.fields().get(0).value());
    assertEquals(1,((Map<?,?>)r.diagnostics().get("rejections")).get("OTHER_OCR_ORIENTATION"));verifyNoInteractions(model);
  }
}
