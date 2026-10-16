package com.sih26190.dms.intake;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sih26190.dms.foli.*;
import com.sih26190.dms.selective.*;
import java.nio.file.*;
import java.util.*;
import static com.sih26190.dms.foli.FoliData.*;

/** Offline benchmark of the actual application classes, not a replacement extractor.
 * Only operator-selected consented/public/synthetic inputs; writes evidence to a
 * local directory. No network, credentials, databases, blockchain or model calls.
 * Original failure documents must never be committed with the output. */
public final class Ps32ExtractionBenchmark {
  public static void main(String[] args) throws Exception {
    if(args.length<2) throw new IllegalArgumentException("Usage: output-directory input.pdf [input.pdf ...]");
    var output=Path.of(args[0]).toAbsolutePath();Files.createDirectories(output);
    var config=new FoliProperties();config.setTempDir(output.resolve("ocr-temp").toString());
    String tess=System.getenv("FOLI_TESSERACT");if(tess!=null&&!tess.isBlank())config.setTesseract(tess);
    config.setMaxPages(30);config.setExtractionTimeoutSeconds(120);config.setOcrTimeoutSeconds(20);
    var extractor=new FoliExtractionService(config,new OcrService(config));
    var facts=new FactSuggestions(new ClaimCanonicalizer(),new CitationVerifier(),null);
    var json=new ObjectMapper();var summaries=new ArrayList<Map<String,Object>>();
    for(int i=1;i<args.length;i++) {
      Path path=Path.of(args[i]).toAbsolutePath();
      if(!Files.isRegularFile(path)||Files.size(path)>config.getMaxBytes())throw new IllegalArgumentException("Invalid or oversized benchmark input");
      String name=path.getFileName().toString(),format=name.substring(name.lastIndexOf('.')+1).toLowerCase(Locale.ROOT);
      if(!Set.of("pdf","txt","csv").contains(format))throw new IllegalArgumentException("Supported input: PDF, TXT, CSV");
      byte[] bytes=Files.readAllBytes(path);String hash=PrivateVault.sha256(bytes);
      var document=new Document("benchmark:"+hash,name,name,format,"BENCHMARK_NOT_VERIFIED","1",true);
      long start=System.nanoTime();var snapshot=extractor.extract(new Source(document,hash,bytes),x -> {});
      long extracted=System.nanoTime();var result=facts.suggest(snapshot,x -> {});long finished=System.nanoTime();
      var receipt=new LinkedHashMap<String,Object>();receipt.put("input",name);receipt.put("source_sha256",hash);
      receipt.put("extractor_version",FoliExtractionService.VERSION);receipt.put("suggestion_version",FactSuggestions.VERSION);
      receipt.put("extraction_seconds",(extracted-start)/1e9);receipt.put("suggestion_seconds",(finished-extracted)/1e9);
      receipt.put("snapshot",snapshot);receipt.put("suggestions",result);receipt.put("model_calls",0);
      receipt.put("issuer_authenticity","NOT_VERIFIED");receipt.put("automatic_confirmation",false);
      json.writerWithDefaultPrettyPrinter().writeValue(output.resolve(name+".json").toFile(),receipt);
      summaries.add(Map.of("input",name,"source_sha256",hash,"pages",snapshot.pages().size(),"fields",result.fields().size(),"extraction_seconds",(extracted-start)/1e9,"suggestion_seconds",(finished-extracted)/1e9));
      json.writerWithDefaultPrettyPrinter().writeValue(output.resolve("summary.json").toFile(),summaries);
      System.out.println(name+" pages="+snapshot.pages().size()+" proposals="+result.fields().size()+" elapsed="+((finished-start)/1e9));
    }
  }
}
