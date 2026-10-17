package com.sih26190.dms.foli;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.*;

/** Fixed fictional benchmark, using the actual application chat and indicator classes. */
public final class P0BenchmarkMain {
  public static void main(String[] args) throws Exception {
    var json=new ObjectMapper();var config=new FoliProperties();
    config.setOllamaUrl(System.getenv().getOrDefault("FOLI_OLLAMA_URL","http://127.0.0.1:11444"));
    config.setTesseract(System.getenv().getOrDefault("FOLI_TESSERACT","tesseract"));
    config.setOcrDataDir(System.getenv().getOrDefault("FOLI_OCR_DATA_DIR",""));
    config.setLayoutPython(System.getenv().getOrDefault("FOLI_LAYOUT_PYTHON",""));
    config.setLayoutScript(System.getenv().getOrDefault("FOLI_LAYOUT_SCRIPT",""));
    config.setTempDir(Path.of(args[1]).toAbsolutePath().getParent().resolve("scratch").toString());
    var rows=new ArrayList<Map<String,Object>>();
    if(args[0].equals("image")) {
      var image=javax.imageio.ImageIO.read(Path.of(args[2]).toFile());
      for(int i=0;i<3;i++) {
        long start=System.nanoTime();var qr=IntakeIndicators.decode(image,config,System.nanoTime()+java.util.concurrent.TimeUnit.SECONDS.toNanos(10));long qrMs=(System.nanoTime()-start)/1_000_000;
        var logo=IntakeIndicators.recognizeLogo(image,new OcrService(config));
        rows.add(Map.of("iteration",i,"qr",qr,"logo",logo,"qrMs",qrMs,"totalMs",(System.nanoTime()-start)/1_000_000));
        System.out.println("IMAGE iteration="+i+" qr="+qr.size()+" logo="+logo.logo().found());
      }
    } else {
      var model=new FoliLocalModel(config);var chat=new FoliChatService(model,new FoliRetrievalService(),new CitationVerifier());
      for(int i=0;i<3;i++) {
        long start=System.nanoTime();var row=new LinkedHashMap<String,Object>();row.put("iteration",i);
        try {row.put("result",chat.chat("Explain selective disclosure in two sentences.",List.of(),null,s -> System.out.println("STAGE "+s)));}
        catch(FoliException e){row.put("failure",e.code());}
        row.put("totalMs",(System.nanoTime()-start)/1_000_000);rows.add(row);
        json.writerWithDefaultPrettyPrinter().writeValue(Path.of(args[1]).toFile(),rows);
        System.out.println("CHAT iteration="+i+" ms="+row.get("totalMs"));
      }
    }
    json.writerWithDefaultPrettyPrinter().writeValue(Path.of(args[1]).toFile(),rows);
  }
}
