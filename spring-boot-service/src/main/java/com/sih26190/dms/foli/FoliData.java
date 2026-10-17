package com.sih26190.dms.foli;

import java.util.List;

/** Source paths/credentials/authoritative facts never enter these API records. */
public final class FoliData {
  private FoliData() {}

  public record Document(String id, String name, String filename, String format,
                         String status, String version, boolean supported) {}
  public record Source(Document document, String hash, byte[] bytes) {}
  public record Word(String text, int start, int end, int left, int top,
                     int width, int height, double confidence, boolean visible) {
    public Word(String text,int start,int end,int left,int top,int width,int height,double confidence) {
      this(text,start,end,left,top,width,height,confidence,true);
    }
  }
  /** Coordinates belong to this layer's upright reading frame, never to an inferred text order. */
  public record Layer(String id,String kind,int rotation,int width,int height,List<Word> words,List<String> warnings,String method) {
    public Layer(String id,String kind,int rotation,int width,int height,List<Word> words,List<String> warnings){this(id,kind,rotation,width,height,words,warnings,kind);}
  }
  public record Page(int number, String text, String status, Double confidence,
                     int firstLine, int lastLine, int rotation,
                     List<Word> words, List<String> warnings,List<Layer> layers) {
    public Page(int number,String text,String status,Double confidence,int firstLine,int lastLine,int rotation,List<Word> words,List<String> warnings) {
      this(number,text,status,confidence,firstLine,lastLine,rotation,words,warnings,List.of());
    }
    public boolean readable() { return !text.isBlank(); }
    public boolean ocr() { return status.contains("OCR"); }
  }
  public record PageInfo(int number, String status, int characters, Double confidence,
                         int firstLine, int lastLine, List<String> warnings) {}
  public record Manifest(String documentId, String name, String format, String version,
                         String sourceHash, String extractorVersion, String ocrEngine,
                         int totalPages, int accountedPages, int readablePages,
                         int ocrPages, int characters, boolean complete,
                         List<PageInfo> pages, List<String> warnings) {}
  public record Snapshot(Document document, String hash, List<Page> pages, Manifest manifest) {}
  public record Citation(String id, String documentId, String sourceHash, String version,
                          int page, int start, int end, String quote, String provenance,
                          boolean sourceVerified, List<String> warnings) {}
}
