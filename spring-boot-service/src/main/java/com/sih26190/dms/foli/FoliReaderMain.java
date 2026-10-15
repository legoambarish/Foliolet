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
    var extractor=new FoliExtractionService(request.config(),new OcrService(request.config()));
    FoliReader.Response response;
    try {
      response=request.mode().equals("render")
          ?new FoliReader.Response(null,extractor.renderPage(request.source(),request.page()),null,null,200)
          :new FoliReader.Response(extractor.extract(request.source(),p -> System.out.println(FoliReader.PROGRESS+p)),null,null,null,200);
    } catch(FoliException e) {
      response=new FoliReader.Response(null,null,e.code(),e.getReason(),e.getStatusCode().value());
    }
    System.out.println(FoliReader.RESULT+json.writeValueAsString(response));
  }
}
