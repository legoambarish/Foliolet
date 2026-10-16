package com.sih26190.dms.foli;

import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class OcrTsvValidationTest {
  String row(String confidence,String width) {return "5\t1\t1\t1\t1\t1\t10\t20\t"+width+"\t12\t"+confidence+"\t90\n";}
  @Test void structuralMinusOneNeverPollutesTheMean() {
    var result=OcrService.parse("1\t1\t0\t0\t0\t0\t0\t0\t100\t100\t-1\t\n"+row("96","20"),0);
    assertEquals(96,result.confidence());assertEquals("90",result.text());
  }
  @Test void invalidConfidenceCannotBypassThresholds() {
    for(String value:List.of("NaN","Infinity","101","-1")) {
      var result=OcrService.parse(row(value,"20"),0);assertTrue(result.words().isEmpty(),value);assertEquals("",result.text());assertEquals(0,result.confidence());
    }
  }
  @Test void malformedGeometryDoesNotLeaveUnboundText() {
    for(String value:List.of("broken","0","-20","2147483647")) {
      var result=OcrService.parse(row("99",value),0);assertTrue(result.words().isEmpty(),value);assertEquals("",result.text());
    }
  }
}
