package com.sih26190.dms.foli;

import com.fasterxml.jackson.databind.ObjectMapper;

/** A narrow child entry point: no Spring application, DB credentials, HTTP server or model client. */
public final class FoliReaderMain {
  private FoliReaderMain() {}
  public static void main(String[] arguments) throws Exception {
    var context=org.slf4j.LoggerFactory.getILoggerFactory();
    if(context instanceof ch.qos.logback.classic.LoggerContext logs) logs.getLogger("ROOT").setLevel(ch.qos.logback.classic.Level.OFF);
    var json=new ObjectMapper();
    var request=json.readValue(System.in,FoliReader.Request.class);
    var ocr=new OcrService(request.config());
    var extractor=new FoliExtractionService(request.config(),ocr);
    FoliReader.Response response;
    try {
      if(request.mode().equals("render")) response=new FoliReader.Response(null,extractor.renderPage(request.source(),request.page()),null,null,200);
      else {
        var snapshot=extractor.extract(request.source(),p -> System.out.println(FoliReader.PROGRESS+p));
        var indicators=request.mode().equals("intake")?new IntakeIndicators(request.config(),extractor,ocr).inspect(request.source(),snapshot):null;
        response=new FoliReader.Response(snapshot,null,null,null,200,indicators);
      }
    } catch(FoliException e) {
      response=new FoliReader.Response(null,null,e.code(),e.getReason(),e.getStatusCode().value());
    }
    System.out.println(FoliReader.RESULT+json.writeValueAsString(response));
  }
}
