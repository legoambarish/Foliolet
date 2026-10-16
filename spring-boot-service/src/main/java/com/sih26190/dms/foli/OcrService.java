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
  public OcrService(FoliProperties config) { this.config = config; }
  public record Result(String text, double confidence, int rotation, List<Word> words, String warning) {}

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
    Result best = new Result("", 0, 0, List.of(), "OCR could not read this page. Review the original.");
    for (int angle : new int[] {0, 90, 180, 270}) {
      if (Thread.currentThread().isInterrupted()) throw new java.util.concurrent.CancellationException();
      if (System.nanoTime() >= deadline) break;
      BufferedImage frame=angle==0?input:rotate(input,angle);
      Result result;
      try { result=run(frame,angle,deadline,3); }
      finally { if(frame!=input) frame.flush(); }
      if (result.confidence() > best.confidence() || best.text().isBlank()) best = result;
      if (!best.text().isBlank() && best.confidence() >= 78) break;
    }
    return best;
  }

  /** Fixed single-block mode for a bounded, geometrically selected logo crop. */
  public Result recognizeBlock(BufferedImage image) {
    return run(image,0,System.nanoTime()+TimeUnit.SECONDS.toNanos(config.getOcrTimeoutSeconds()),6);
  }

  private Result run(BufferedImage image, int angle, long deadline,int segmentation) {
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
      return parse(Files.readString(tsv, StandardCharsets.UTF_8), angle);
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
