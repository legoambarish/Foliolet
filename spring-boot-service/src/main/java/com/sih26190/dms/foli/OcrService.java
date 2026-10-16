package com.sih26190.dms.foli;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import javax.imageio.ImageIO;
import org.springframework.stereotype.Service;
import static com.sih26190.dms.foli.FoliData.*;

/** Fixed executable/arguments, no shell, URLs or model-supplied process input. */
@Service
public class OcrService {
  private final FoliProperties config;
  private long hardDeadline=Long.MAX_VALUE;
  public OcrService(FoliProperties config) { this.config = config; }
  public void limitUntil(long deadline){hardDeadline=deadline;}
  public record Result(String text, double confidence, int rotation, List<Word> words, String warning,String method) {
    public Result(String text,double confidence,int rotation,List<Word> words,String warning){this(text,confidence,rotation,words,warning,"tesseract-page");}
  }

  public String version() {
    Process process = null;
    try {
      process = new ProcessBuilder(config.getTesseract(), "--version").redirectErrorStream(true).start();
      if (!process.waitFor(3, TimeUnit.SECONDS)) return "unavailable";
      String version = new String(process.getInputStream().readNBytes(200), StandardCharsets.UTF_8).lines().findFirst().orElse("");
      return process.exitValue() == 0 && version.startsWith("tesseract 5") ? version : "unavailable";
    } catch (Exception e) { return "unavailable";
    } finally { if (process != null && process.isAlive()) process.destroyForcibly(); }
  }

  public Result recognize(BufferedImage input) {
    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(config.getOcrTimeoutSeconds());
    return recognize(input,deadline);
  }

  private Result recognize(BufferedImage input,long deadline) {
    Result best = new Result("", 0, 0, List.of(), "OCR could not read this page. Review the original.");
    for (int angle : new int[] {0, 90, 180, 270}) {
      if (Thread.currentThread().isInterrupted()) throw new java.util.concurrent.CancellationException();
      if (System.nanoTime() >= deadline) break;
      BufferedImage frame=angle==0?input:rotate(input,angle);
      Result result;
      try { result=run(frame,angle,deadline,3); }
      finally { if(frame!=input) frame.flush(); }
      if (quality(result)>quality(best) || best.text().isBlank()) best = result;
      if (!best.text().isBlank() && best.confidence() >= 88 && best.words().size()>=5) break;
    }
    return best;
  }

  /** Complementary page/block segmentations share one deadline and retain separate provenance. */
  public List<Result> recognizeLayout(BufferedImage input) {
    long deadline=Math.min(hardDeadline,System.nanoTime()+TimeUnit.SECONDS.toNanos(config.getOcrTimeoutSeconds()));
    boolean compact=!config.getLayoutPython().isBlank() && !config.getLayoutScript().isBlank();
    long tessDeadline=compact?Math.min(deadline,System.nanoTime()+TimeUnit.SECONDS.toNanos(Math.max(5,config.getOcrTimeoutSeconds()-12))):deadline;
    var readings=new ArrayList<Result>();var original=run(input,0,tessDeadline,3);readings.add(original);
    if(System.nanoTime()<tessDeadline)readings.add(run(input,0,tessDeadline,6));
    var best=readings.stream().max(java.util.Comparator.comparingDouble(OcrService::quality)).orElse(original);
    best=readings.stream().max(java.util.Comparator.comparingDouble(OcrService::quality)).orElse(original);
    if(best.confidence()<85 || best.words().size()<5)for(int angle:new int[]{90,180,270}) {
      if(System.nanoTime()>=tessDeadline)break;var frame=rotate(input,angle);
      try {var r=run(frame,angle,tessDeadline,3);readings.add(r);if(quality(r)>quality(best))best=r;}
      finally {frame.flush();}
      if(best.confidence()>=88 && best.words().size()>=5)break;
    }
    if(best.rotation()!=0 && System.nanoTime()<tessDeadline) {
      var frame=rotate(input,best.rotation());try {readings.add(run(frame,best.rotation(),tessDeadline,6));}finally{frame.flush();}
    }
    if(best.confidence()<85 || best.words().size()<5) {
      for(int threshold:new int[]{160,200}) {
        if(System.nanoTime()>=tessDeadline)break;
        int angle=best.rotation();var upright=angle==0?input:rotate(input,angle);
        var frame=contrast(upright,threshold);if(upright!=input)upright.flush();
        try {
          var r=run(frame,angle,tessDeadline,6);
          readings.add(new Result(r.text(),r.confidence(),r.rotation(),r.words(),r.warning(),"tesseract-psm6-contrast-threshold-"+threshold));
        } finally {frame.flush();}
      }
    }
    best=readings.stream().max(java.util.Comparator.comparingDouble(OcrService::quality)).orElse(original);
    if(compact && (best.confidence()<85 || best.words().size()<5) && System.nanoTime()<deadline) {
      int angle=best.rotation();var frame=angle==0?input:rotate(input,angle);
      Result extra;try{extra=runCompact(frame,deadline);}finally{if(frame!=input)frame.flush();}
      if(extra.text().isBlank()) {
        original=new Result(original.text(),original.confidence(),original.rotation(),original.words(),original.warning()+" "+extra.warning(),original.method());readings.set(0,original);
      } else readings.add(new Result(extra.text(),extra.confidence(),angle,extra.words(),extra.warning(),extra.method()));
    }
    readings.removeIf(r -> r.text().isBlank());readings.sort(java.util.Comparator.comparingDouble(OcrService::quality).reversed());
    if(readings.isEmpty())return List.of(original);
    // Keep the original rendering's reading as a check even if a processed frame reads better.
    var kept=new ArrayList<Result>();kept.add(readings.get(0));if(original!=readings.get(0) && !original.text().isBlank())kept.add(original);
    for(var r:readings)if(kept.size()<4 && !kept.contains(r))kept.add(r);
    return List.copyOf(kept);
  }

  private Result runCompact(BufferedImage image,long deadline) {
    Path png=null,output=null;Process process=null;
    try {
      Path root=Path.of(config.getTempDir()).toAbsolutePath().normalize();Files.createDirectories(root);
      png=Files.createTempFile(root,"layout-",".png");output=Files.createTempFile(root,"layout-",".json");
      ImageIO.write(image,"png",png.toFile());
      process=new ProcessBuilder(config.getLayoutPython(),"-I",config.getLayoutScript(),"--input",png.toString(),"--output",output.toString())
          .redirectOutput(ProcessBuilder.Redirect.DISCARD).redirectError(ProcessBuilder.Redirect.DISCARD).start();
      long remaining=Math.max(1,TimeUnit.NANOSECONDS.toMillis(Math.min(deadline,hardDeadline)-System.nanoTime()));
      if(!process.waitFor(remaining,TimeUnit.MILLISECONDS)) {
        process.destroyForcibly();process.waitFor(2,TimeUnit.SECONDS);
        return new Result("",0,0,List.of(),"Local layout OCR reached its time budget; Tesseract readings were retained.","rapidocr-timeout");
      }
      if(process.exitValue()!=0 || Files.size(output)>2_000_000)throw new IllegalStateException();
      var payload=new com.fasterxml.jackson.databind.ObjectMapper().readTree(Files.readString(output,StandardCharsets.UTF_8));
      String text=payload.path("text").asText();var words=new ArrayList<Word>();
      if(text.length()>config.getMaxPageCharacters() || payload.path("words").size()>2048)throw new IllegalStateException();
      for(var w:payload.path("words")) {
        String value=w.path("text").asText();int from=w.path("start").asInt(-1),to=w.path("end").asInt(-1);
        int left=w.path("left").asInt(-1),top=w.path("top").asInt(-1),width=w.path("width").asInt(),height=w.path("height").asInt();
        double confidence=w.path("confidence").asDouble(-1);
        if(from<0 || to>text.length() || from>=to || !text.substring(from,to).equals(value) || left<0 || top<0 || width<=0 || height<=0
            || left+width>image.getWidth() || top+height>image.getHeight() || !Double.isFinite(confidence) || confidence<0 || confidence>100)throw new IllegalStateException();
        words.add(new Word(value,from,to,left,top,width,height,confidence));
      }
      return new Result(text,words.stream().mapToDouble(Word::confidence).average().orElse(0),0,List.copyOf(words),
          "Independent local OCR transcription; check critical values against the original.","rapidocr-3.10.0-ppocrv6-small-cpu");
    } catch(InterruptedException e){Thread.currentThread().interrupt();throw new java.util.concurrent.CancellationException();}
    catch(Exception e){return new Result("",0,0,List.of(),"Local layout OCR unavailable or failed integrity checks; Tesseract readings were retained.","rapidocr-unavailable");}
    finally {
      if(process!=null && process.isAlive())process.destroyForcibly();
      for(Path file:new Path[]{png,output})if(file!=null)try{Files.deleteIfExists(file);}catch(Exception ignored){}
    }
  }
  private static BufferedImage contrast(BufferedImage input,int threshold) {
    int w=input.getWidth(),h=input.getHeight();var histogram=new int[256];
    for(int y=0;y<h;y++)for(int x=0;x<w;x++){int rgb=input.getRGB(x,y);histogram[(int)((rgb>>16&255)*.299+(rgb>>8&255)*.587+(rgb&255)*.114)]++;}
    int low=0,high=255,sum=0,cut=Math.max(1,w*h/100);
    for(int i=0;i<256;i++){sum+=histogram[i];if(sum>=cut){low=i;break;}}
    sum=0;for(int i=255;i>=0;i--){sum+=histogram[i];if(sum>=cut){high=i;break;}}
    var out=new BufferedImage(w,h,BufferedImage.TYPE_BYTE_BINARY);
    for(int y=0;y<h;y++)for(int x=0;x<w;x++) {
      int rgb=input.getRGB(x,y),gray=(int)((rgb>>16&255)*.299+(rgb>>8&255)*.587+(rgb&255)*.114);
      int normalized=high<=low?gray:(gray-low)*255/(high-low);out.setRGB(x,y,normalized>threshold?0xffffffff:0xff000000);
    }
    return out;
  }
  private static double quality(Result result) {
    // A handful of confident garbage tokens must not beat a coherent page at another rotation.
    return result.words().stream().mapToDouble(w -> w.confidence()<45?0:Math.min(20,w.text().length())*w.confidence()/100).sum();
  }

  /** Fixed single-block mode for a bounded, geometrically selected logo crop. */
  public Result recognizeBlock(BufferedImage image) {
    return run(image,0,System.nanoTime()+TimeUnit.SECONDS.toNanos(config.getOcrTimeoutSeconds()),6);
  }

  private Result run(BufferedImage image, int angle, long deadline,int segmentation) {
    deadline=Math.min(deadline,hardDeadline);
    if(System.nanoTime()>=deadline)return new Result("",0,angle,List.of(),"OCR reading budget reached; review the original.","not processed");
    Path png = null, tsv = null;
    Process process = null;
    try {
      Path root = Path.of(config.getTempDir()).toAbsolutePath().normalize();
      Files.createDirectories(root);
      png = Files.createTempFile(root, "ocr-", ".png");
      tsv = Files.createTempFile(root, "ocr-", ".tsv");
      ImageIO.write(image, "png", png.toFile());
      var builder = new ProcessBuilder(config.getTesseract(), png.toString(), "stdout", "-l",
          config.getOcrLanguage(), "--psm", Integer.toString(segmentation), "-c", "tessedit_create_tsv=1");
      if (!config.getOcrDataDir().isBlank()) builder.environment().put("TESSDATA_PREFIX", config.getOcrDataDir());
      builder.environment().put("OMP_THREAD_LIMIT", "2");
      process = builder.redirectOutput(tsv.toFile()).redirectError(ProcessBuilder.Redirect.DISCARD).start();
      long remaining = Math.max(1, TimeUnit.NANOSECONDS.toMillis(deadline - System.nanoTime()));
      if (!process.waitFor(remaining, TimeUnit.MILLISECONDS)) {
        process.destroyForcibly(); process.waitFor(2, TimeUnit.SECONDS);
        return new Result("", 0, angle, List.of(), "OCR timed out. Review the original page.");
      }
      if (process.exitValue() != 0 || Files.size(tsv) > 2_000_000) throw new IllegalStateException();
      var parsed=parse(Files.readString(tsv, StandardCharsets.UTF_8), angle);
      return new Result(parsed.text(),parsed.confidence(),parsed.rotation(),parsed.words(),parsed.warning(),"tesseract-psm"+segmentation);
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt(); throw new java.util.concurrent.CancellationException();
    } catch (Exception e) {
      return new Result("", 0, angle, List.of(), "OCR unavailable or failed. Review the original page.");
    } finally {
      if (process != null && process.isAlive()) {
        process.destroyForcibly();
        try { process.waitFor(2, TimeUnit.SECONDS); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
      }
      for (Path file : new Path[] {png, tsv}) if (file != null) {
        try { Files.deleteIfExists(file); } catch (Exception ignored) { /* OS may retain a locked temp file; no source is changed. */ }
      }
    }
  }

  static Result parse(String tsv, int angle) {
    var text = new StringBuilder(); var words = new ArrayList<Word>();
    String lastLine = ""; double sum = 0; int weight = 0;
    for (String row : tsv.split("\\R")) {
      String[] c = row.split("\t", 12);
      if (c.length < 12 || !c[0].equals("5") || c[11].isBlank()) continue;
      try {
        double confidence = Double.parseDouble(c[10]);
        if (confidence < 0) continue;
        String line = c[1] + ":" + c[2] + ":" + c[3] + ":" + c[4];
        if (!text.isEmpty()) text.append(line.equals(lastLine) ? ' ' : '\n');
        int start = text.length(); text.append(c[11]);
        words.add(new Word(c[11], start, text.length(), Integer.parseInt(c[6]), Integer.parseInt(c[7]),
            Integer.parseInt(c[8]), Integer.parseInt(c[9]), confidence));
        sum += confidence * c[11].length(); weight += c[11].length(); lastLine = line;
      } catch (NumberFormatException ignored) { }
    }
    double confidence = weight == 0 ? 0 : sum / weight;
    return new Result(text.toString(), confidence, angle, List.copyOf(words),
        confidence < 78 ? "OCR confidence is low. Check wording and numbers on the original page." : "OCR transcription; verify critical wording against the original.");
  }

  private static BufferedImage rotate(BufferedImage image, int angle) {
    boolean swap = angle == 90 || angle == 270;
    var result = new BufferedImage(swap ? image.getHeight() : image.getWidth(),
        swap ? image.getWidth() : image.getHeight(), BufferedImage.TYPE_INT_RGB);
    Graphics2D g = result.createGraphics(); g.setColor(Color.WHITE); g.fillRect(0, 0, result.getWidth(), result.getHeight());
    g.translate(result.getWidth()/2.0, result.getHeight()/2.0); g.rotate(Math.toRadians(angle));
    g.drawImage(image, -image.getWidth()/2, -image.getHeight()/2, null); g.dispose(); return result;
  }
}
