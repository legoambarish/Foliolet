package com.sih26190.dms.foli;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.nio.file.Path;
import java.util.List;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.font.*;
import org.apache.pdfbox.pdmodel.graphics.image.LosslessFactory;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Explicit live gate: -Dtest=FoliOcrLiveIT with FOLI_TESSERACT configured. */
class FoliOcrLiveIT {
  @TempDir Path temp;
  FoliProperties config; OcrService ocr;
  @BeforeEach void setup() {
    config = new FoliProperties(); config.setTempDir(temp.toString());
    config.setTesseract(System.getenv().getOrDefault("FOLI_TESSERACT", "tesseract"));
    config.setOcrDataDir(System.getenv().getOrDefault("FOLI_OCR_DATA_DIR", ""));
    ocr = new OcrService(config);
    assertTrue(ocr.version().startsWith("tesseract 5"), "Install local Tesseract for the live OCR gate");
  }
  static BufferedImage scan() {
    var image = new BufferedImage(1600,650,BufferedImage.TYPE_INT_RGB);
    var g = image.createGraphics(); g.setColor(Color.WHITE); g.fillRect(0,0,1600,650);
    g.setColor(Color.BLACK); g.setFont(new Font("Arial",Font.PLAIN,42));
    g.drawString("Cancellation: no renewal fee unless notice is late.",70,180);
    g.drawString("The hidden fee is INR 9300 after 30 days.",70,270); g.dispose(); return image;
  }
  @Test void realTesseractReadsNegationAndAmount() {
    var result = ocr.recognize(scan());
    assertTrue(result.text().contains("unless")); assertTrue(result.text().contains("9300"));
    assertTrue(result.confidence()>78); assertFalse(result.words().isEmpty());
    for (var word : result.words()) assertEquals(word.text(),result.text().substring(word.start(),word.end()));
  }
  @Test void rotatedScanIsRecoveredWithProvenance() {
    var input=scan(); var rotated=new BufferedImage(input.getHeight(),input.getWidth(),BufferedImage.TYPE_INT_RGB);
    var g=rotated.createGraphics(); g.translate(rotated.getWidth(),0); g.rotate(Math.PI/2); g.drawImage(input,0,0,null); g.dispose();
    var result=ocr.recognize(rotated); assertTrue(result.text().contains("9300")); assertTrue(result.text().contains("unless"));
    assertTrue(result.rotation()!=0 || result.confidence()>78);
  }
  @Test void mixedPdfIncludesImageTextAndNativeText() throws Exception {
    byte[] bytes;
    try (var pdf=new PDDocument(); var output=new ByteArrayOutputStream()) {
      var page=new PDPage(); pdf.addPage(page);
      try (var stream=new PDPageContentStream(pdf,page)) {
        stream.beginText(); stream.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA),12);
        stream.newLineAtOffset(45,740); stream.showText("Contract overview: monthly service obligations."); stream.endText();
        stream.drawImage(LosslessFactory.createFromImage(pdf,scan()),20,350,570,230);
      }
      pdf.save(output); bytes=output.toByteArray();
    }
    var snapshot=new FoliExtractionService(config,ocr).extract(FoliReadingTest.source(bytes,"pdf"),ignored -> {});
    assertEquals("MIXED_OCR",snapshot.pages().get(0).status());
    assertTrue(snapshot.pages().get(0).text().contains("9300"));
    assertTrue(snapshot.pages().get(0).text().contains("Contract overview")); assertFalse(snapshot.manifest().complete());
  }
  @Test void missingOcrAndTimeoutCleanIntermediates() throws Exception {
    config.setTesseract(temp.resolve("missing.exe").toString());
    var result=new OcrService(config).recognize(scan()); assertTrue(result.text().isBlank());
    try (var files=java.nio.file.Files.list(temp)) { assertEquals(0,files.count()); }
  }
}
