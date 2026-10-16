package com.sih26190.dms.intake;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sih26190.dms.foli.*;
import com.sih26190.dms.selective.*;
import java.nio.file.*;
import java.util.*;

/** Local-only benchmark adapter. Document text/results go only to the requested private file. */
public final class IntakeBenchmarkMain {
  public static void main(String[] args) throws Exception {
    var json=new ObjectMapper(); var input=Path.of(args[0]); var output=Path.of(args[1]);
    var config=new FoliProperties();
    config.setTesseract(System.getenv().getOrDefault("FOLI_TESSERACT","tesseract"));
    config.setOcrDataDir(System.getenv().getOrDefault("FOLI_OCR_DATA_DIR",""));
    config.setLayoutPython(System.getenv().getOrDefault("FOLI_LAYOUT_PYTHON",""));
    config.setLayoutScript(System.getenv().getOrDefault("FOLI_LAYOUT_SCRIPT",""));
    config.setOllamaUrl(System.getenv().getOrDefault("FOLI_OLLAMA_URL","http://127.0.0.1:11444"));
    config.setTempDir(output.toAbsolutePath().getParent().resolve("scratch").toString());
    var facts=new FactSuggestions(new ClaimCanonicalizer(),new CitationVerifier(),new FoliLocalModel(config));
    byte[] bytes=Files.readAllBytes(input);String hash=PrivateVault.sha256(bytes);
    var source=new FoliData.Source(new FoliData.Document("wallet:0x"+"b".repeat(64),"Private benchmark",input.getFileName().toString(),
        input.toString().endsWith(".pdf")?"pdf":"txt","DRAFT","1",true),hash,bytes);
    long start=System.nanoTime();var inspected=new FoliReader(config).inspect(source,ignored -> {});
    long readMs=(System.nanoTime()-start)/1_000_000;Object result;String failure=null;
    try {result=facts.suggest(inspected.snapshot(),ignored -> {});}
    catch(Exception e) {result=null;failure=e instanceof FoliException f?f.code():e.getClass().getSimpleName();}
    var out=new LinkedHashMap<String,Object>();out.put("snapshot",inspected.snapshot());out.put("indicators",inspected.indicators());
    out.put("result",result);out.put("failure",failure);out.put("readingMs",readMs);out.put("totalMs",(System.nanoTime()-start)/1_000_000);
    Files.createDirectories(output.toAbsolutePath().getParent());json.writeValue(output.toFile(),out);
    System.out.println("BENCHMARK_COMPLETE "+input.getFileName()+" "+out.get("totalMs")+"ms");
  }
}
