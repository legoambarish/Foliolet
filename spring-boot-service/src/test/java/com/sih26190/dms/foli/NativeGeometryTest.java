package com.sih26190.dms.foli;

import com.sih26190.dms.intake.FactSuggestions;
import com.sih26190.dms.selective.*;
import java.io.ByteArrayOutputStream;
import java.util.*;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.font.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static com.sih26190.dms.foli.FoliData.*;

class NativeGeometryTest {
  @Test void actualPdfBoxGeometryRetainsExactSourceWordsAndTableScores() throws Exception {
    byte[] bytes;
    try(var pdf=new PDDocument();var out=new ByteArrayOutputStream()) {
      var page=new PDPage();pdf.addPage(page);
      try(var stream=new PDPageContentStream(pdf,page)) {
        String[][] rows={{"Subject","Maximum","Obtained"},{"Math","100","90"},{"Science","100","80"}};
        for(int y=0;y<rows.length;y++) for(int x=0;x<rows[y].length;x++) {
          stream.beginText();stream.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA),12);
          stream.newLineAtOffset(45+x*180,720-y*35);stream.showText(rows[y][x]);stream.endText();
        }
      }
      pdf.save(out);bytes=out.toByteArray();
    }
    var ocr=mock(OcrService.class);var config=new FoliProperties();
    var doc=new Document("wallet:0x"+"a".repeat(64),"Synthetic native marks","marks.pdf","pdf","DRAFT","1",true);
    var snapshot=new FoliExtractionService(config,ocr).extract(new Source(doc,PrivateVault.sha256(bytes),bytes),s -> {});
    var page=snapshot.pages().get(0);assertEquals("TEXT",page.status());assertEquals(9,page.words().size(),page.toString());
    for(var w:page.words()) assertEquals(w.text(),page.text().substring(w.start(),w.end()));
    var result=new FactSuggestions(new ClaimCanonicalizer(),new CitationVerifier(),mock(FoliLocalModel.class)).suggest(snapshot,s -> {});
    assertEquals(2,result.fields().size(),result.toString());assertEquals(Set.of("90","80"),new HashSet<>(result.fields().stream().map(FactSuggestions.Candidate::value).toList()));
    verifyNoInteractions(ocr);
  }
}
