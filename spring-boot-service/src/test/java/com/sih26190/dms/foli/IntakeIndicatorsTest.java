package com.sih26190.dms.foli;

import com.google.zxing.*;
import com.google.zxing.qrcode.QRCodeWriter;
import com.sih26190.dms.selective.PrivateVault;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.util.*;
import java.util.List;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.graphics.image.LosslessFactory;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static com.sih26190.dms.foli.FoliData.*;

class IntakeIndicatorsTest {
  static BufferedImage qr(String payload,int size) throws Exception {
    var bits=new QRCodeWriter().encode(payload,BarcodeFormat.QR_CODE,size,size);
    var image=new BufferedImage(size,size,BufferedImage.TYPE_INT_RGB);
    for(int y=0;y<size;y++) for(int x=0;x<size;x++) image.setRGB(x,y,bits.get(x,y)?0xff000000:0xffffffff);
    return image;
  }
  static BufferedImage rotated(BufferedImage input) {
    var out=new BufferedImage(input.getHeight(),input.getWidth(),BufferedImage.TYPE_INT_RGB);
    for(int y=0;y<input.getHeight();y++) for(int x=0;x<input.getWidth();x++) out.setRGB(input.getHeight()-1-y,x,input.getRGB(x,y));
    return out;
  }
  @Test void onlyExactVerificationOriginIsSpecificAndNeverExecuted() {
    assertEquals("DIGILOCKER_VERIFICATION_ORIGIN",IntakeIndicators.qrKind("https://verify.digilocker.gov.in/synthetic?id=not-a-real-id"));
    for(String s:List.of("https://example.com/","https://verify.digilocker.gov.in.evil.example/","https://verify.digilocker.gov.in@evil.example/",
        "http://verify.digilocker.gov.in/","file:///secret","javascript:alert(1)","https://verify.digilocker.gov.in:443/",
        "https://verify.digilocker.gov.in/%2e%2e/a","https://www.digilocker.gov.in/","not a URL"))
      assertEquals("GENERIC_QR_FOUND",IntakeIndicators.qrKind(s),s);
  }
  @Test void scaledRotatedInvertedAndMultipleCodesKeepOnlyHashes() throws Exception {
    for(int size:List.of(130,260)) {
      var image=qr("https://verify.digilocker.gov.in/synthetic",size);
      for(var frame:List.of(image,rotated(image))) {
        var result=IntakeIndicators.decode(frame); assertEquals(1,result.size()); assertEquals("DIGILOCKER_VERIFICATION_ORIGIN",result.get(0).kind());
        assertEquals(64,result.get(0).payloadHash().length()); assertFalse(result.toString().contains("https:"));
        for(int y=0;y<frame.getHeight();y++) for(int x=0;x<frame.getWidth();x++) frame.setRGB(x,y,frame.getRGB(x,y)^0x00ffffff);
        assertEquals(1,IntakeIndicators.decode(frame).size());
      }
    }
    var both=new BufferedImage(650,320,BufferedImage.TYPE_INT_RGB); var g=both.createGraphics(); g.setColor(Color.WHITE);g.fillRect(0,0,650,320);
    g.drawImage(qr("https://verify.digilocker.gov.in/synthetic",260),20,20,null);g.drawImage(qr("https://example.com/",260),350,20,null);g.dispose();
    assertEquals(Set.of("DIGILOCKER_VERIFICATION_ORIGIN","GENERIC_QR_FOUND"),new HashSet<>(IntakeIndicators.decode(both).stream().map(IntakeIndicators.Qr::kind).toList()));
  }
  @Test void corruptCroppedAndBlankCodesNeverInventPayloads() throws Exception {
    var input=qr("https://example.com/",260);
    assertTrue(IntakeIndicators.decode(input.getSubimage(100,100,100,100)).isEmpty());
    assertTrue(IntakeIndicators.decode(new BufferedImage(100,100,BufferedImage.TYPE_INT_RGB)).isEmpty());
    assertThrows(IllegalArgumentException.class,() -> IntakeIndicators.decode(new BufferedImage(3000,3000,BufferedImage.TYPE_BYTE_GRAY)));
  }
  @Test void wordmarkGeometryAcceptsGraphicButRejectsProseAndLoneBrandName() {
    var image=new BufferedImage(700,200,BufferedImage.TYPE_INT_RGB);var g=image.createGraphics();g.setColor(new Color(110,50,230));g.fillRect(300,50,350,100);g.dispose();
    var words=List.of(new Word("Powered",0,7,310,65,65,15,95),new Word("by",8,10,380,65,20,15,95),new Word("DigiLocker",11,21,310,95,280,35,96));
    assertTrue(IntakeIndicators.logo(image,new OcrService.Result("Powered by\nDigiLocker",96,0,words,"")).found());
    assertFalse(IntakeIndicators.logo(image,new OcrService.Result("DigiLocker",96,0,List.of(new Word("DigiLocker",0,10,310,95,280,35,96)),"")).found());
    assertFalse(IntakeIndicators.logo(image,new OcrService.Result("This is Powered by DigiLocker in prose",96,0,List.of(new Word("Powered",8,15,310,65,65,15,95),new Word("DigiLocker",19,29,310,95,280,35,96)),"")).found());
  }
  @Test void lastPageForgedQrStaysPossibleAndSafetyGapsStayExplicit() throws Exception {
    byte[] bytes;
    try(var doc=new PDDocument();var out=new java.io.ByteArrayOutputStream()) {
      for(int i=0;i<3;i++) {var page=new PDPage();doc.addPage(page);if(i==2)try(var c=new PDPageContentStream(doc,page)){c.drawImage(LosslessFactory.createFromImage(doc,qr("https://verify.digilocker.gov.in/synthetic-forgery",260)),80,400,200,200);}}
      doc.save(out); bytes=out.toByteArray();
    }
    var source=new Source(new Document("wallet:0x"+"a".repeat(64),"Forged fixture","forged.pdf","pdf","DRAFT","1",true),PrivateVault.sha256(bytes),bytes);
    var config=new FoliProperties();var ocr=mock(OcrService.class);
    when(ocr.recognize(any())).thenReturn(new OcrService.Result("Synthetic page",95,0,List.of(),""));when(ocr.version()).thenReturn("test OCR");
    var extraction=new FoliExtractionService(config,ocr);var snapshot=extraction.extract(source,x -> {});
    var result=new IntakeIndicators(config,extraction,ocr).inspect(source,snapshot);
    assertEquals("POSSIBLE_DIGILOCKER_FORMAT",result.status()); assertFalse(result.pages().get(2).qr().isEmpty());
    assertEquals(3,result.inspectedPages()); assertFalse(result.toString().contains("ISSUER_VERIFIED"));
    config.setMaxPages(2);var capped=new IntakeIndicators(config,extraction,ocr).inspect(source,extraction.extract(source,x -> {}));
    assertEquals("INCONCLUSIVE",capped.status());assertFalse(capped.pages().get(2).inspected());assertFalse(capped.warnings().isEmpty());
  }
}
