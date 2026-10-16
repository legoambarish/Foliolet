package com.sih26190.dms.foli;

import java.io.*;
import java.nio.*;
import java.nio.charset.*;
import java.util.*;
import java.util.concurrent.CancellationException;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.encryption.InvalidPasswordException;
import org.apache.pdfbox.pdmodel.graphics.image.PDImageXObject;
import org.apache.pdfbox.pdmodel.graphics.form.PDFormXObject;
import org.apache.pdfbox.rendering.*;
import org.apache.pdfbox.text.*;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import static com.sih26190.dms.foli.FoliData.*;

@Service
public class FoliExtractionService {
  public static final String VERSION = "foli-pages-2";
  private final FoliProperties config;
  private final OcrService ocr;
  public FoliExtractionService(FoliProperties config, OcrService ocr) { this.config = config; this.ocr = ocr; }

  public Snapshot extract(Source source, Consumer<String> progress) {
    if (!source.document().supported()) throw new FoliException(HttpStatus.UNSUPPORTED_MEDIA_TYPE,
        "UNSUPPORTED_FORMAT", "Foli currently reads PDF, UTF-8 TXT and CSV. This file type is not supported.");
    List<Page> pages;
    try {
      pages = source.document().format().equals("pdf") ? pdf(source.bytes(), progress) : text(source.bytes(), progress);
    } catch (InvalidPasswordException e) {
      throw new FoliException(HttpStatus.UNPROCESSABLE_CONTENT, "PROTECTED_PDF", "This PDF requires a password. Foli cannot read it.");
    } catch (CharacterCodingException e) {
      throw new FoliException(HttpStatus.UNPROCESSABLE_CONTENT, "INVALID_TEXT", "The source is not valid UTF-8 text.");
    } catch (IOException e) {
      throw new FoliException(HttpStatus.UNPROCESSABLE_CONTENT, "CORRUPT_SOURCE", "This document could not be parsed. Check the original file.");
    }
    int readable = (int) pages.stream().filter(Page::readable).count();
    int ocrPages = (int) pages.stream().filter(Page::ocr).count();
    int characters = pages.stream().mapToInt(p -> p.text().length()).sum();
    boolean complete = readable == pages.size() && pages.stream().allMatch(p -> p.warnings().isEmpty() && p.status().equals("TEXT"));
    var warnings = new ArrayList<String>();
    if (!complete) warnings.add("Some pages are uncertain or unprocessed. Do not infer that an unlocated term is absent.");
    if (!source.document().format().equals("pdf")) warnings.add("Page numbers are text segments; locations refer to physical UTF-8 lines, not PDF pages or parsed CSV records.");
    var manifest = new Manifest(source.document().id(), source.document().name(), source.document().format(),
        source.document().version(), source.hash(), VERSION, ocrPages > 0 ? ocr.version() : "not used",
        pages.size(), pages.size(), readable, ocrPages, characters, complete,
        pages.stream().map(p -> new PageInfo(p.number(), p.status(), p.text().length(), p.confidence(),
            p.firstLine(), p.lastLine(), p.warnings())).toList(), List.copyOf(warnings));
    return new Snapshot(source.document(), source.hash(), List.copyOf(pages), manifest);
  }

  private List<Page> pdf(byte[] bytes, Consumer<String> progress) throws IOException {
    var result = new ArrayList<Page>(); int characters = 0;
    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(config.getExtractionTimeoutSeconds());
    try (PDDocument document = Loader.loadPDF(bytes)) {
      if(document.getNumberOfPages()==0) throw new FoliException(HttpStatus.UNPROCESSABLE_CONTENT,"EMPTY_PDF","This PDF has no pages to read.");
      if (document.getNumberOfPages() > 5000) throw new FoliException(HttpStatus.PAYLOAD_TOO_LARGE,
          "PAGE_COUNT_LIMIT", "This PDF exceeds the 5000-page accounting safety ceiling; no review was completed.");
      PDFRenderer renderer = new PDFRenderer(document); renderer.setSubsamplingAllowed(true);
      var documentWarnings=new ArrayList<String>();
      var catalog=document.getDocumentCatalog();
      if(catalog.getOpenAction()!=null) documentWarnings.add("PDF opening actions are ignored and never executed.");
      if(catalog.getNames()!=null && catalog.getNames().getEmbeddedFiles()!=null)
        documentWarnings.add("Embedded attachments are not read. Review them separately in a suitable viewer.");
      if(catalog.getAcroForm()!=null && catalog.getAcroForm().hasXFA())
        documentWarnings.add("Dynamic XFA form content may not render completely. Foli cannot guarantee coverage of those fields.");
      for (int i = 0; i < document.getNumberOfPages(); i++) {
        checkCancel(); int number = i + 1;
        progress.accept("Reading page " + number + "/" + document.getNumberOfPages());
        if (i >= config.getMaxPages() || characters >= config.getMaxCharacters() || System.nanoTime() > deadline) {
          result.add(empty(number, "SKIPPED_LIMIT", "Page not processed: page, character or extraction-time budget reached.")); continue;
        }
        try {
          PDPage page = document.getPage(i);
          boolean images = hasImage(page.getResources(), 0, Collections.newSetFromMap(new IdentityHashMap<>()),new long[2]);
          boolean forms=page.getAnnotations().stream().anyMatch(a -> a instanceof org.apache.pdfbox.pdmodel.interactive.annotation.PDAnnotationWidget);
          var stripper = new QualityStripper(config.getMaxPageCharacters(), deadline); stripper.setSortByPosition(true);
          stripper.setStartPage(number); stripper.setEndPage(number);
          String nativeText = stripper.getText(document);
          if (nativeText.length() > config.getMaxPageCharacters()) {
            result.add(empty(number, "SKIPPED_LIMIT", "Page text exceeds the character safety limit.")); continue;
          }
          boolean suspicious = nativeText.strip().length() < 24 || nativeText.indexOf('\ufffd') >= 0
              || nativeText.chars().filter(c -> Character.isISOControl(c) && !Character.isWhitespace(c)).count() > 3;
          var warnings = new ArrayList<String>();
          if(i==0) warnings.addAll(documentWarnings);
          if(forms) warnings.add("PDF form widgets detected; embedded text and rendered-page OCR must be compared.");
          if (stripper.tiny) warnings.add("Very small print detected; check the rendered original.");
          if (stripper.columns) warnings.add("Separated columns or table cells detected. Extracted reading order may differ from the visual page; inspect the original before interpreting scope.");
          String text = nativeText; String status = "TEXT"; Double confidence = null;
          List<Word> words = List.of(); int rotation = 0;
          if (suspicious || images || forms) {
            progress.accept("OCR page " + number + "/" + document.getNumberOfPages());
            var image = render(renderer, page, i, 200);
            var recognized = ocr.recognize(image); image.flush();
            confidence = recognized.confidence(); rotation = recognized.rotation();
            warnings.add(recognized.warning());
            if (!recognized.text().isBlank()) {
              if (nativeText.isBlank() || suspicious) {
                text = recognized.text(); words = recognized.words(); status = confidence < 78 ? "OCR_UNCERTAIN" : "OCR";
              } else {
                status = "MIXED_OCR";
                if (!nativeText.replaceAll("\\s+", " ").strip().equals(recognized.text().replaceAll("\\s+", " ").strip())) {
                  text = nativeText + "\n[Rendered-page OCR transcription]\n" + recognized.text();
                  int offset=nativeText.length()+"\n[Rendered-page OCR transcription]\n".length();
                  words=recognized.words().stream().map(w -> new Word(w.text(),w.start()+offset,w.end()+offset,w.left(),w.top(),w.width(),w.height(),w.confidence())).toList();
                  warnings.add("Embedded text and rendered-page OCR differ. Both readings retained; visually resolve contradictions.");
                } else {
                  // Map matching OCR words to native offsets without rewriting retained text.
                  var mapped=new ArrayList<Word>(); int cursor=0;
                  for(var w:recognized.words()) {
                    int at=nativeText.indexOf(w.text(),cursor);
                    if(at<0) {mapped.clear();break;}
                    mapped.add(new Word(w.text(),at,at+w.text().length(),w.left(),w.top(),w.width(),w.height(),w.confidence()));cursor=at+w.text().length();
                  }
                  words=List.copyOf(mapped);
                }
              }
            } else if (nativeText.isBlank()) { text = ""; status = "UNREADABLE";
            } else { status = "TEXT_UNCERTAIN"; warnings.add("Image/suspicious content could not be checked with OCR."); }
          }
          if (text.length() > config.getMaxPageCharacters() || characters + text.length() > config.getMaxCharacters()) {
            result.add(empty(number, "SKIPPED_LIMIT", "Extracted text exceeds the safety budget; no partial text was silently kept.")); continue;
          }
          characters += text.length();
          result.add(new Page(number, text, status, confidence, 0, 0, rotation, words, List.copyOf(warnings)));
        } catch (CancellationException e) { throw e;
        } catch (TextBudgetException e) { result.add(empty(number, "SKIPPED_LIMIT", "Page exceeds text or parsing-time budget."));
        } catch (Exception e) { result.add(empty(number, "FAILED", "Page extraction or rendering failed. Review the original.")); }
      }
    }
    return result;
  }

  private List<Page> text(byte[] bytes, Consumer<String> progress) throws CharacterCodingException {
    String input = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
        .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
    var result = new ArrayList<Page>(); int line = 1, firstLine = 1, used = 0;
    var segment = new StringBuilder();
    // Keep delimiters and exact text; segment locations are explicit physical lines.
    var matcher = java.util.regex.Pattern.compile("[^\\r\\n]*(?:\\r\\n|\\r|\\n|$)").matcher(input);
    while (matcher.find()) {
      checkCancel(); if (matcher.start() == matcher.end()) continue;
      segment.append(matcher.group());
      if (line - firstLine >= 79 || segment.length() >= 6000 || matcher.end() == input.length()) {
        int number = result.size() + 1; progress.accept("Reading text segment " + number);
        if (number > config.getMaxPages() || used + segment.length() > config.getMaxCharacters()
            || segment.length() > config.getMaxPageCharacters()) {
          result.add(new Page(number, "", "SKIPPED_LIMIT", null, firstLine, line, 0, List.of(), List.of("Text segment exceeds processing limits.")));
        } else {
          result.add(new Page(number, segment.toString(), segment.toString().isBlank() ? "UNREADABLE" : "TEXT",
              null, firstLine, line, 0, List.of(), segment.toString().isBlank() ? List.of("No readable text.") : List.of()));
          used += segment.length();
        }
        firstLine = line + 1; segment.setLength(0);
      }
      line++;
    }
    if (result.isEmpty()) result.add(empty(1, "UNREADABLE", "No readable text."));
    return result;
  }

  public byte[] renderPage(Source source, int number) {
    if (!source.document().format().equals("pdf")) throw new FoliException(HttpStatus.BAD_REQUEST, "NO_RENDER", "Original page preview is available for PDF only.");
    try (var document = Loader.loadPDF(source.bytes())) {
      if (number < 1 || number > document.getNumberOfPages()) throw AuthorizedDocumentResolver.missing();
      hasImage(document.getPage(number-1).getResources(),0,Collections.newSetFromMap(new IdentityHashMap<>()),new long[2]);
      var renderer = new PDFRenderer(document); renderer.setSubsamplingAllowed(true);
      var image = render(renderer, document.getPage(number-1), number-1, 130);
      var output = new ByteArrayOutputStream(); javax.imageio.ImageIO.write(image, "png", output); image.flush(); return output.toByteArray();
    } catch (IOException e) { throw AuthorizedDocumentResolver.failure("SOURCE_UNAVAILABLE", "Original page preview unavailable."); }
  }

  private java.awt.image.BufferedImage render(PDFRenderer renderer, PDPage page, int index, int desiredDpi) throws IOException {
    double w = page.getCropBox().getWidth(), h = page.getCropBox().getHeight();
    if (!Double.isFinite(w*h) || w <= 0 || h <= 0) throw new IOException("Invalid page dimensions");
    float dpi = (float) Math.min(desiredDpi, 72 * Math.sqrt(config.getMaxPixels() / (w*h)));
    if (dpi < 20) throw new IOException("Page dimensions exceed rendering ceiling");
    return renderer.renderImageWithDPI(index, dpi, ImageType.RGB);
  }
  private static boolean hasImage(PDResources resources, int depth, Set<Object> ancestors,long[] budget) throws IOException {
    if(resources==null) return false;
    if(depth>10 || !ancestors.add(resources.getCOSObject())) throw new IOException("Nested/cyclic PDF resources exceed the safety budget");
    boolean found=false;
    try {
      for(var name:resources.getXObjectNames()) {
        checkCancel(); if(++budget[1]>5000) throw new IOException("PDF resource count exceeds the safety budget");
        var object=resources.getXObject(name);
        if(object instanceof PDImageXObject image) {
          long pixels=(long)image.getWidth()*image.getHeight(); budget[0]+=pixels;
          if(image.getWidth()<=0 || image.getHeight()<=0 || pixels>80_000_000 || budget[0]>100_000_000)
            throw new IOException("PDF decoded-image dimensions exceed the safety budget");
          found=true;
        }
        if(object instanceof PDFormXObject form) found=hasImage(form.getResources(),depth+1,ancestors,budget) || found;
      }
    } finally { ancestors.remove(resources.getCOSObject()); }
    return found;
  }
  static Page empty(int page, String status, String warning) { return new Page(page, "", status, null, 0, 0, 0, List.of(), List.of(warning)); }
  static void checkCancel() { if (Thread.currentThread().isInterrupted()) throw new CancellationException(); }
  private static class QualityStripper extends PDFTextStripper {
    boolean tiny,columns; int count; final int maximum; final long deadline;
    final Map<Integer,double[]> rows=new HashMap<>();
    QualityStripper(int maximum, long deadline) throws IOException { super(); this.maximum=maximum; this.deadline=deadline; }
    @Override protected void processTextPosition(TextPosition position) {
      checkCancel();
      if (++count > maximum || System.nanoTime()>deadline) throw new TextBudgetException();
      if (position.getFontSizeInPt() < 6) tiny = true;
      int row=(int)Math.round(position.getYDirAdj()/3);
      double x=position.getXDirAdj(),end=x+position.getWidthDirAdj();
      var bounds=rows.get(row);
      if(bounds==null) rows.put(row,new double[]{x,end});
      else { if(x-bounds[1]>60 || bounds[0]-end>60) columns=true; bounds[0]=Math.min(bounds[0],x); bounds[1]=Math.max(bounds[1],end); }
      super.processTextPosition(position);
    }
  }
  private static class TextBudgetException extends RuntimeException {}
}
