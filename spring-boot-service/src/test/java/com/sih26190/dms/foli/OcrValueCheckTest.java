package com.sih26190.dms.foli;

import java.util.List;
import org.junit.jupiter.api.Test;
import static com.sih26190.dms.foli.FoliData.*;
import static org.junit.jupiter.api.Assertions.*;

class OcrValueCheckTest {
  private OcrService.Result reading(String token,double confidence) {
    return new OcrService.Result(token,97,0,List.of(new Word(token,0,token.length(),10,10,100,20,confidence)),"fixture");
  }
  @Test void aHighPageAverageCannotHideAWeakIdentifierOrScore() {
    assertTrue(OcrService.needsValueCheck(reading("Z200XX0001",74)));
    assertTrue(OcrService.needsValueCheck(reading("086",65)));
    assertFalse(OcrService.needsValueCheck(reading("0000719",98)));
    assertFalse(OcrService.needsValueCheck(reading("Heading",65)));
    assertFalse(OcrService.needsValueCheck(reading("|",30)));
    assertFalse(OcrService.needsValueCheck(reading("91",12)));
  }
}
