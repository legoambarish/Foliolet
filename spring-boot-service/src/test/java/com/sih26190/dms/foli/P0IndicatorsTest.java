package com.sih26190.dms.foli;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.util.*;

class P0IndicatorsTest {
  @Test void observedEnvelopeIsOnlyFormatDetectionAndUnknownVariantsStayUnknown() throws Exception {
    String encoded=Base64.getEncoder().encodeToString(new byte[256]);
    String payload="[\"5005\",\"1\",\"Y\",\""+encoded+"\"]";
    assertEquals("DIGILOCKER_ASSOCIATED_STRUCTURED",IntakeIndicators.qrKind(payload));
    // Fabrication passes a format check, NEVER authentication.
    assertFalse(IntakeIndicators.qrKind(payload).contains("VERIFIED"));
    for(String bad:new String[]{payload.replace("5005","9999"),payload.replace("\"1\"","\"2\""),
        payload.replace(encoded,"not-base64"),"[\"5005\",\"1\",\"Y\"]",payload+"trailing"})
      assertFalse(IntakeIndicators.associated(IntakeIndicators.qrKind(bad)),bad);
    var decoded=IntakeIndicators.decode(IntakeIndicatorsTest.qr(payload,400));
    assertEquals(1,decoded.size());assertEquals("DIGILOCKER_ASSOCIATED_STRUCTURED",decoded.get(0).kind());
    assertFalse(decoded.toString().contains(encoded));
  }
  @Test void completeGraphicMatchesScaleRotationAndMonochromeButNotSolidLookalike() throws Exception {
    var logo=javax.imageio.ImageIO.read(getClass().getResourceAsStream("/indicators/digilocker-brand.png"));
    for(int factor:new int[]{1,2,4})for(boolean mono:new boolean[]{false,true}) {
      var canvas=new BufferedImage(logo.getWidth()*factor+100,logo.getHeight()*factor+100,BufferedImage.TYPE_INT_RGB);
      var g=canvas.createGraphics();g.setColor(Color.WHITE);g.fillRect(0,0,canvas.getWidth(),canvas.getHeight());g.drawImage(logo,30,30,logo.getWidth()*factor,logo.getHeight()*factor,null);g.dispose();
      if(mono)for(int y=0;y<canvas.getHeight();y++)for(int x=0;x<canvas.getWidth();x++) {
        int rgb=canvas.getRGB(x,y);int gray=((rgb>>16&255)+(rgb>>8&255)+(rgb&255))/3;canvas.setRGB(x,y,new Color(gray,gray,gray).getRGB());
      }
      assertTrue(BrandingTemplate.match(canvas).found(),factor+" mono="+mono);
      assertTrue(BrandingTemplate.match(IntakeIndicatorsTest.rotated(canvas)).found());
    }
    var fake=new BufferedImage(200,90,BufferedImage.TYPE_INT_RGB);var g=fake.createGraphics();g.setColor(Color.WHITE);g.fillRect(0,0,200,90);g.setColor(new Color(110,60,255));g.fillRoundRect(5,5,174,72,20,20);g.dispose();
    assertFalse(BrandingTemplate.match(fake).found());
  }
  @Test void noCloudTextLeavesWithoutBothPolicyAndConsent() {
    for(var model:java.util.List.of(new FoliGeminiModel(false,"paid-reviewed","fake","gemini-3.5-flash-lite"),
        new FoliGeminiModel(true,"unverified","fake","gemini-3.5-flash-lite"),
        new FoliGeminiModel(true,"paid-reviewed","","gemini-3.5-flash-lite"))) {
      assertFalse(model.available());assertThrows(FoliException.class,()->model.ask(true,"sensitive","private",null));
    }
    var paid=new FoliGeminiModel(true,"paid-reviewed","fake","gemini-3.5-flash-lite");
    assertThrows(FoliException.class,()->paid.ask(false,"sensitive","private",null));
  }
}
