package com.sih26190.dms.foli;

import java.awt.image.BufferedImage;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import com.sih26190.dms.selective.PrivateVault;

/** Private local IPC. Only hashes, format labels and bounds escape this method. */
final class ComplementaryQr {
  static List<IntakeIndicators.Qr> decode(BufferedImage image,FoliProperties config,long deadline) {
    if(config.getLayoutPython().isBlank() || config.getLayoutScript().isBlank() || System.nanoTime()>=deadline)return List.of();
    Path input=null,output=null;Process process=null;
    try {
      Path script=Path.of(config.getLayoutScript()).toAbsolutePath().resolveSibling("qr-decode-worker.py");
      if(!Files.isRegularFile(script))return List.of();
      Path root=Path.of(config.getTempDir()).toAbsolutePath();Files.createDirectories(root);
      input=Files.createTempFile(root,"qr-",".png");output=Files.createTempFile(root,"qr-",".json");
      javax.imageio.ImageIO.write(image,"png",input.toFile());
      var builder=new ProcessBuilder(config.getLayoutPython(),"-I",script.toString(),input.toString())
          .redirectOutput(output.toFile()).redirectError(ProcessBuilder.Redirect.DISCARD);
      builder.environment().keySet().removeIf(k -> !Set.of("PATH","SYSTEMROOT","WINDIR","TEMP","TMP").contains(k.toUpperCase(Locale.ROOT)));
      process=builder.start();
      long ms=Math.max(1,Math.min(5000,TimeUnit.NANOSECONDS.toMillis(deadline-System.nanoTime())));
      if(!process.waitFor(ms,TimeUnit.MILLISECONDS) || process.exitValue()!=0 || Files.size(output)>100_000)return List.of();
      var values=new com.fasterxml.jackson.databind.ObjectMapper().readTree(Files.readString(output));
      if(!values.isArray() || values.size()>16)return List.of();
      var results=new ArrayList<IntakeIndicators.Qr>();
      for(var value:values) {
        String text=value.path("text").asText();if(text.length()>4096)continue;
        int left=value.path("left").asInt(-1),top=value.path("top").asInt(-1),right=value.path("right").asInt(-1),bottom=value.path("bottom").asInt(-1);
        if(left<0 || top<0 || right<=left || bottom<=top || right>image.getWidth() || bottom>image.getHeight())continue;
        byte[] bytes=text.getBytes(java.nio.charset.StandardCharsets.UTF_8);
        results.add(new IntakeIndicators.Qr(IntakeIndicators.qrKind(text),PrivateVault.sha256(bytes),bytes.length,new IntakeIndicators.Bounds(left,top,right,bottom)));
      }
      return List.copyOf(results);
    }catch(InterruptedException e){Thread.currentThread().interrupt();throw new java.util.concurrent.CancellationException();}
    catch(Exception ignored){return List.of();}
    finally {
      if(process!=null && process.isAlive()) {process.destroyForcibly();try{process.waitFor(2,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}
      for(var path:new Path[]{input,output})if(path!=null)try{Files.deleteIfExists(path);}catch(Exception ignored){}
    }
  }
}
