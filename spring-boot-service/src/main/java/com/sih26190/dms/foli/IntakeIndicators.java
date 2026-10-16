package com.sih26190.dms.foli;

import com.google.zxing.*;
import com.google.zxing.common.HybridBinarizer;
import com.google.zxing.multi.qrcode.QRCodeMultiReader;
import com.sih26190.dms.selective.PrivateVault;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.List;
import java.util.concurrent.TimeUnit;
import static com.sih26190.dms.foli.FoliData.*;

/** Offline pixel/QR heuristics, deliberately without any authenticity or network API. */
public final class IntakeIndicators {
  public static final String VERSION="intake-indicators-2-coverage";
  public record Bounds(float left,float top,float right,float bottom) {}
  public record Qr(String kind,String payloadHash,int payloadLength,Bounds bounds) {}
  public record PageResult(int page,boolean inspected,boolean logo,double logoScore,String logoEvidence,
                           List<Qr> qr,List<String> warnings,boolean qrInspected,boolean logoInspected) {
    public PageResult(int page,boolean inspected,boolean logo,double logoScore,String logoEvidence,List<Qr> qr,List<String> warnings){this(page,inspected,logo,logoScore,logoEvidence,qr,warnings,inspected,inspected);}
  }
  public record Report(String version,String sourceHash,String status,int totalPages,int inspectedPages,
                       List<PageResult> pages,List<String> warnings,int qrInspectedPages,int logoInspectedPages) {
    public Report(String version,String sourceHash,String status,int totalPages,int inspectedPages,List<PageResult> pages,List<String> warnings){this(version,sourceHash,status,totalPages,inspectedPages,pages,warnings,inspectedPages,inspectedPages);}
  }
  private final FoliProperties config;
  private final FoliExtractionService extraction;
  private final OcrService ocr;
  public IntakeIndicators(FoliProperties config,FoliExtractionService extraction,OcrService ocr) {
    this.config=config; this.extraction=extraction; this.ocr=ocr;
  }
  public Report inspect(Source source,Snapshot snapshot) {
    return inspect(source,snapshot,System.nanoTime()+TimeUnit.SECONDS.toNanos(config.getExtractionTimeoutSeconds()));
  }
  public Report inspect(Source source,Snapshot snapshot,long deadline) {
    ocr.limitUntil(deadline);
    if(!source.document().format().equals("pdf")) return new Report(VERSION,source.hash(),"NO_DIGILOCKER_INDICATOR",snapshot.pages().size(),snapshot.pages().size(),List.of(),List.of("Text/CSV has no rendered DigiLocker graphic to inspect."));
    var pages=new ArrayList<PageResult>(); int inspected=0,logoInspected=0; boolean possible=false,weak=false;
    for(var page:snapshot.pages()) {
      FoliExtractionService.checkCancel();
      if(page.number()>config.getMaxPages() || System.nanoTime()+TimeUnit.SECONDS.toNanos(2)>deadline || page.status().equals("SKIPPED_LIMIT") || page.status().equals("FAILED")) {
        pages.add(new PageResult(page.number(),false,false,0,"Not inspected",List.of(),List.of("Page omitted by the safety budget or parser failure."))); continue;
      }
      try {
        byte[] png=extraction.renderPage(source,page.number());
        var image=javax.imageio.ImageIO.read(new java.io.ByteArrayInputStream(png));
        try {
          var cached=cachedReading(page,image);var qr=decode(image);
          int previous=config.getOcrTimeoutSeconds();config.setOcrTimeoutSeconds((int)Math.max(1,Math.min(previous,TimeUnit.NANOSECONDS.toSeconds(deadline-System.nanoTime())-1)));
          LogoReading graphic;
          try {graphic=recognizeLogo(image,ocr,cached);}finally{config.setOcrTimeoutSeconds(previous);}
          var logo=graphic.logo();
          weak|=logo.score()>0 && !logo.found();
          boolean readable=graphic.readable();
          // No OCR means a missing logo is unknown, even if the QR decoder found nothing.
          var warnings=new ArrayList<String>();
          if(!readable) warnings.add("Logo OCR unavailable or unreadable; no absence claim for this page.");
          if(logo.score()>0 && !logo.found()) warnings.add("Weak DigiLocker text/graphic resemblance; inspect the original.");
          pages.add(new PageResult(page.number(),true,logo.found(),logo.score(),logo.evidence(),qr,List.copyOf(warnings),true,readable));
          inspected++;if(readable)logoInspected++;
          possible|=logo.found() || qr.stream().anyMatch(q -> q.kind().equals("DIGILOCKER_VERIFICATION_ORIGIN"));
        } finally { image.flush(); }
      } catch(java.util.concurrent.CancellationException e) { throw e;
      } catch(Exception e) { pages.add(new PageResult(page.number(),false,false,0,"Rendering failed",List.of(),List.of("Indicator inspection failed; review the original."))); }
    }
    boolean partial=inspected<snapshot.pages().size() || logoInspected<snapshot.pages().size() || weak;
    return new Report(VERSION,source.hash(),possible?"POSSIBLE_DIGILOCKER_FORMAT":partial?"INCONCLUSIVE":"NO_DIGILOCKER_INDICATOR",
        snapshot.pages().size(),inspected,List.copyOf(pages),partial?List.of("QR and logo coverage are reported separately. Weak or uninspected indicators establish no source origin."):List.of(),inspected,logoInspected);
  }
  private static OcrService.Result cachedReading(Page page,BufferedImage image) {
    if(page.layers()==null)return null;
    var layer=page.layers().stream().filter(l -> l.id().equals("ocr")).findFirst()
        .orElseGet(() -> page.layers().stream().filter(l -> l.kind().equals("NATIVE")).findFirst().orElse(null));
    if(layer==null || layer.words().isEmpty())return null;
    double width=layer.rotation()%180==0?image.getWidth():image.getHeight(),height=layer.rotation()%180==0?image.getHeight():image.getWidth();
    var words=layer.words().stream().filter(Word::visible).map(w -> new Word(w.text(),w.start(),w.end(),
        (int)Math.round(w.left()*width/layer.width()),(int)Math.round(w.top()*height/layer.height()),
        Math.max(1,(int)Math.round(w.width()*width/layer.width())),Math.max(1,(int)Math.round(w.height()*height/layer.height())),w.confidence())).toList();
    return new OcrService.Result(page.text(),words.stream().mapToDouble(Word::confidence).average().orElse(0),layer.rotation(),words,"Reused source-position reading",layer.method());
  }
  public static String qrKind(String payload) {
    if(payload==null || payload.length()>4096) return "UNKNOWN_QR";
    try {
      var u=URI.create(payload);
      if("https".equals(u.getScheme()) && "verify.digilocker.gov.in".equalsIgnoreCase(u.getHost())
          && u.getUserInfo()==null && u.getPort()==-1 && u.getFragment()==null && u.getRawPath()!=null
          && !u.getRawPath().contains("%") && !u.getRawPath().contains("..")) return "DIGILOCKER_VERIFICATION_ORIGIN";
    } catch(IllegalArgumentException ignored) {}
    return "GENERIC_QR_FOUND";
  }
  public static List<Qr> decode(BufferedImage image) {
    int width=image.getWidth(),height=image.getHeight();
    if((long)width*height>8_000_000) throw new IllegalArgumentException("Pixel budget exceeded");
    var found=new LinkedHashMap<String,Qr>();
    // ZXing handles quarter turns and multiple codes; inverted pass supports dark graphics.
    var luminance=new RGBLuminanceSource(width,height,image.getRGB(0,0,width,height,null,0,width));
    for(var source:List.of(luminance,luminance.invert())) {
      try {
        var hints=new EnumMap<DecodeHintType,Object>(DecodeHintType.class);
        hints.put(DecodeHintType.TRY_HARDER,true); hints.put(DecodeHintType.POSSIBLE_FORMATS,List.of(BarcodeFormat.QR_CODE));
        for(var result:new QRCodeMultiReader().decodeMultiple(new BinaryBitmap(new HybridBinarizer(source)),hints)) {
          String text=result.getText(); byte[] raw=result.getRawBytes();
          byte[] hashBytes=raw==null?(text==null?new byte[0]:text.getBytes(StandardCharsets.UTF_8)):raw;
          String hash=PrivateVault.sha256(hashBytes);
          float left=width,top=height,right=0,bottom=0;
          for(var p:result.getResultPoints()) { left=Math.min(left,p.getX()); top=Math.min(top,p.getY()); right=Math.max(right,p.getX()); bottom=Math.max(bottom,p.getY()); }
          if(found.size()<16) found.putIfAbsent(hash,new Qr(qrKind(text),hash,Math.min(hashBytes.length,4096),new Bounds(left,top,right,bottom)));
        }
      } catch(NotFoundException ignored) {}
    }
    return List.copyOf(found.values());
  }
  public record Logo(boolean found,double score,String evidence) {}
  public record LogoReading(Logo logo,boolean readable) {}
  public static LogoReading recognizeLogo(BufferedImage image,OcrService ocr) {
    return recognizeLogo(image,ocr,null);
  }
  private static LogoReading recognizeLogo(BufferedImage image,OcrService ocr,OcrService.Result cached) {
    var recognized=cached==null?ocr.recognize(image):cached; var first=logo(image,recognized);
    if(!first.found()) {
      var template=graphicTemplate(image,ocr);
      if(template.found()) return new LogoReading(template,true);
      if(template.score()>first.score()) first=template;
    }
    // Small supplied/downloaded graphics lose their thin Powered-by lettering.
    // One bounded interpolation pass improves OCR without a vision model. No
    // document or QR data leaves this child process.
    if(!first.found() && Math.max(image.getWidth(),image.getHeight())<=1000) {
      double scale=Math.min(4,1200d/Math.max(image.getWidth(),image.getHeight()));
      var enlarged=new BufferedImage((int)(image.getWidth()*scale),(int)(image.getHeight()*scale),BufferedImage.TYPE_INT_RGB);
      var g=enlarged.createGraphics(); g.setRenderingHint(RenderingHints.KEY_INTERPOLATION,RenderingHints.VALUE_INTERPOLATION_BICUBIC);
      g.drawImage(image,0,0,enlarged.getWidth(),enlarged.getHeight(),null);g.dispose();
      try {
        var result=ocr.recognize(enlarged);var candidate=logo(enlarged,result);
        if(candidate.found() || candidate.score()>first.score()) return new LogoReading(candidate,!result.text().isBlank());
      } finally { enlarged.flush(); }
    }
    return new LogoReading(first,!recognized.text().isBlank());
  }
  private static boolean purple(int rgb) {
    int r=rgb>>16&255,g=rgb>>8&255,b=rgb&255;
    return r>g*1.2 && b>g*1.2 && b>60 && r<235;
  }
  /** A coarse ring + attached rectangle feature template, calibrated on the
   * supplied graphic. It proposes an OCR crop; copied shapes have zero issuer authority. */
  private static Logo graphicTemplate(BufferedImage image,OcrService ocr) {
    double scale=Math.min(1,1000d/Math.max(image.getWidth(),image.getHeight()));
    var sample=new BufferedImage(Math.max(1,(int)(image.getWidth()*scale)),Math.max(1,(int)(image.getHeight()*scale)),BufferedImage.TYPE_INT_RGB);
    var sg=sample.createGraphics();sg.drawImage(image,0,0,sample.getWidth(),sample.getHeight(),null);sg.dispose();
    boolean resemblance=false; int attempted=0;
    try {
      for(int angle=0;angle<4;angle++) {
        int w=sample.getWidth(),h=sample.getHeight(),n=w*h;
        byte[] mask=new byte[n]; for(int y=0;y<h;y++) for(int x=0;x<w;x++) if(purple(sample.getRGB(x,y))) mask[y*w+x]=1;
        int[] queue=new int[n];
        for(int origin=0;origin<n;origin++) {
          if(mask[origin]!=1) continue;
          int count=1,read=0,left=origin%w,right=left,top=origin/w,bottom=top;queue[0]=origin;mask[origin]=2;
          while(read<count) {
            int p=queue[read++],x=p%w,y=p/w;left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);
            for(int neighbor:new int[]{x>0?p-1:-1,x+1<w?p+1:-1,y>0?p-w:-1,y+1<h?p+w:-1})
              if(neighbor>=0 && mask[neighbor]==1) {mask[neighbor]=2;queue[count++]=neighbor;}
          }
          int cw=right-left+1,ch=bottom-top+1;
          if(ch<16 || cw<ch*2 || cw>ch*4.5 || count<cw*ch*.2 || count>cw*ch*.85) continue;
          int ring=0;
          for(int a=110;a<=250;a+=10) {double rad=Math.toRadians(a);int x=left+(int)(ch*(.5+.47*Math.cos(rad))),y=top+(int)(ch*(.5+.47*Math.sin(rad)));if(x>=0&&x<w&&y>=0&&y<h&&purple(sample.getRGB(x,y)))ring++;}
          if(ring<9) continue;
          resemblance=true;if(++attempted>4) return new Logo(false,.3,"Purple graphic resemblance; wordmark OCR was inconclusive");
          int x0=left+(int)(ch*.96),y0=top+(int)(ch*.16),cropW=right-x0,cropH=(int)(ch*.72);
          if(cropW<20 || cropH<10) continue;
          var crop=new BufferedImage(cropW*3,cropH*3,BufferedImage.TYPE_INT_RGB);
          for(int y=0;y<cropH;y++) for(int x=0;x<cropW;x++) {
            int rgb=sample.getRGB(x0+x,y0+y),r=rgb>>16&255,g=rgb>>8&255,b=rgb&255;
            int ink=r+g+b>600?0xff000000:0xffffffff;
            for(int yy=0;yy<3;yy++) for(int xx=0;xx<3;xx++) crop.setRGB(x*3+xx,y*3+yy,ink);
          }
          try {
            var text=ocr.recognizeBlock(crop);
            if(text!=null && logo(crop,text).found()) return new Logo(true,.94,"Purple ring and wordmark-block template with matching Powered-by OCR");
          } finally {crop.flush();}
        }
        var rotated=new BufferedImage(h,w,BufferedImage.TYPE_INT_RGB);
        var g=rotated.createGraphics();g.translate(h,0);g.rotate(Math.PI/2);g.drawImage(sample,0,0,null);g.dispose();sample.flush();sample=rotated;
      }
    } finally {sample.flush();}
    return new Logo(false,resemblance?.3:0,resemblance?"Purple graphic resemblance; wordmark OCR was inconclusive":"No matching graphic template");
  }
  public static Logo logo(BufferedImage image,OcrService.Result recognized) {
    // A geometric text template: complete short Powered-by block next to a large
    // DigiLocker wordmark. A mention embedded in prose does not fit this layout.
    var words=recognized.words();
    for(int i=0;i<words.size();i++) {
      var word=words.get(i);
      if(!word.text().replaceAll("[^A-Za-z]","").equalsIgnoreCase("DigiLocker") || word.confidence()<65) continue;
      int lineStart=recognized.text().lastIndexOf('\n',Math.max(0,word.start()-1))+1;
      int lineEnd=recognized.text().indexOf('\n',word.end()); if(lineEnd<0) lineEnd=recognized.text().length();
      String line=recognized.text().substring(lineStart,lineEnd).strip();
      if(!line.matches("(?i)(?:powered\\s+by\\s+)?digi\\s*locker[®™]?") ) continue;
      boolean powered=false;
      boolean vertical=word.height()>word.width()*2;
      for(var p:words) if(p.text().equalsIgnoreCase("Powered") && p.confidence()>60
          && (vertical
            ? Math.abs(p.top()-word.top())<word.height()*1.5 && Math.abs(p.left()-word.left())<word.width()*4
            : Math.abs(p.left()-word.left())<word.width()*1.5 && Math.abs(p.top()-word.top())<word.height()*4)) powered=true;
      if(!powered) continue;
      // Purple ink density is corroborating graphic evidence, not a trust anchor.
      double purple=purpleFraction(image,word,recognized.rotation());
      int major=Math.max(word.width(),word.height()),minor=Math.min(word.width(),word.height());
      boolean proportions=minor>0 && major>=minor*2 && major<=minor*14;
      double score=proportions?(purple>.08?.92:.78):.35;
      return new Logo(proportions,score,purple>.08?"Powered-by wordmark layout with purple graphic pixels":"Powered-by wordmark layout (monochrome or low color)");
    }
    return new Logo(false,recognized.text().toLowerCase(Locale.ROOT).contains("digilocker")?.2:0,"No qualified Powered-by wordmark layout");
  }
  private static double purpleFraction(BufferedImage image,Word word,int rotation) {
    // OCR coordinates are rotated; color is only measured in the matching frame.
    if(rotation!=0) return 0;
    int count=0,purple=0;
    for(int y=Math.max(0,word.top());y<Math.min(image.getHeight(),word.top()+word.height());y+=2)
      for(int x=Math.max(0,word.left());x<Math.min(image.getWidth(),word.left()+word.width());x+=2) {
        int rgb=image.getRGB(x,y),r=rgb>>16&255,g=rgb>>8&255,b=rgb&255; count++;
        if(r>g*1.2 && b>g*1.2 && b>60 && r<235) purple++;
      }
    return count==0?0:(double)purple/count;
  }
}
