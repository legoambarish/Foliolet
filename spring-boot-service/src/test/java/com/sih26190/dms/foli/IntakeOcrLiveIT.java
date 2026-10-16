package com.sih26190.dms.foli;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.nio.file.*;
import javax.imageio.ImageIO;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

/** Opt-in test on the supplied graphic. Never prints, persists or follows QR payloads. */
class IntakeOcrLiveIT {
  @Test void suppliedWordmarkAtMultipleScalesAndRotation() throws Exception {
    String reference=System.getenv("INTAKE_REFERENCE_IMAGE"),executable=System.getenv("FOLI_TESSERACT");
    Assumptions.assumeTrue(reference!=null && executable!=null,"Set both reference image and local Tesseract to run this gate");
    var config=new FoliProperties();config.setTesseract(executable);config.setOcrDataDir(System.getenv().getOrDefault("FOLI_OCR_DATA_DIR",""));
    config.setTempDir(Path.of("target/intake-ocr-live").toAbsolutePath().toString());
    var ocr=new OcrService(config);assertNotEquals("unavailable",ocr.version());
    var image=ImageIO.read(Path.of(reference).toFile());assertNotNull(image);
    // This supplied reference has QR left, wordmark right. Only the wordmark is
    // used as a logo calibration target, without storing a derivative fixture.
    var wordmark=image.getSubimage(image.getWidth()/2,0,image.getWidth()-image.getWidth()/2,image.getHeight());
    for(double scale:new double[]{1,0.7,1.6}) {
      var frame=new BufferedImage((int)(wordmark.getWidth()*scale),(int)(wordmark.getHeight()*scale),BufferedImage.TYPE_INT_RGB);
      var g=frame.createGraphics();g.setColor(Color.WHITE);g.fillRect(0,0,frame.getWidth(),frame.getHeight());g.drawImage(wordmark,0,0,frame.getWidth(),frame.getHeight(),null);g.dispose();
      var result=ocr.recognize(frame);var logo=IntakeIndicators.recognizeLogo(frame,ocr).logo();
      System.out.println("REFERENCE_LOGO scale="+scale+" detected="+logo.found()+" score="+logo.score()+" ocrConfidence="+result.confidence());
      if(!logo.found()) {
        var zoom=new BufferedImage(frame.getWidth()*4,frame.getHeight()*4,BufferedImage.TYPE_INT_RGB);
        var zg=zoom.createGraphics();zg.setRenderingHint(RenderingHints.KEY_INTERPOLATION,RenderingHints.VALUE_INTERPOLATION_BICUBIC);zg.drawImage(frame,0,0,zoom.getWidth(),zoom.getHeight(),null);zg.dispose();
        var zoomOcr=ocr.recognize(zoom);
        System.out.println("REFERENCE_SMALL wordmarkText="+zoomOcr.text().replace('\n',' ')+" words="+zoomOcr.words());
      }
      assertTrue(logo.found(),"Reference wordmark at scale "+scale);
      var rotated=IntakeIndicatorsTest.rotated(frame);var rotatedOcr=ocr.recognize(rotated);
      System.out.println("REFERENCE_ROTATION scale="+scale+" angle="+rotatedOcr.rotation()+" confidence="+rotatedOcr.confidence()+" wordmarkText="+rotatedOcr.text().replace('\n',' '));
      assertTrue(IntakeIndicators.recognizeLogo(rotated,ocr).logo().found(),"Rotated reference wordmark at scale "+scale);
    }
  }
}
