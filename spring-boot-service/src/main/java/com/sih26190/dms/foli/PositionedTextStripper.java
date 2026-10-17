package com.sih26190.dms.foli;

import java.io.*;
import java.util.*;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.*;
import static com.sih26190.dms.foli.FoliData.*;

/** Captures offsets at PDFBox's actual output writer, after sorting and Unicode normalization. */
final class PositionedTextStripper extends PDFTextStripper {
  private final int maximum; private final long deadline; private int count;
  private StringWriter writer; private final List<Word> words=new ArrayList<>();
  private final IdentityHashMap<TextPosition,Boolean> visibility=new IdentityHashMap<>();
  private final Map<Integer,double[]> rows=new HashMap<>();
  private final Map<Integer,List<TextPosition>> glyphRows=new HashMap<>();
  boolean tiny,columns,hidden,overlapping; int unmapped;
  PositionedTextStripper(int maximum,long deadline) throws IOException {this.maximum=maximum;this.deadline=deadline;setSortByPosition(true);}
  String extract(PDDocument document,int number) throws IOException {
    setStartPage(number);setEndPage(number);writer=new StringWriter();writeText(document,writer);return writer.toString();
  }
  List<Word> words(){return List.copyOf(words);}
  @Override protected void processTextPosition(TextPosition p) {
    FoliExtractionService.checkCancel();
    if(++count>maximum || System.nanoTime()>deadline) throw new BudgetExceeded();
    boolean visible=getGraphicsState().getTextState().getRenderingMode()!=org.apache.pdfbox.pdmodel.graphics.state.RenderingMode.NEITHER
        && p.getWidthDirAdj()>0 && p.getHeightDir()>0;
    // Invisible text is retained for full-document reading but cannot silently become a supported fact.
    visibility.put(p,visible);hidden|=!visible;tiny|=p.getFontSizeInPt()<6;
    int row=(int)Math.round(p.getYDirAdj()/3);double x=p.getXDirAdj(),end=x+p.getWidthDirAdj();var bounds=rows.get(row);
    var glyphs=glyphRows.computeIfAbsent(row,ignored -> new ArrayList<>());
    if(glyphs.size()>4096)throw new BudgetExceeded();
    for(var prior:glyphs) {
      double overlap=Math.min(end,prior.getXDirAdj()+prior.getWidthDirAdj())-Math.max(x,prior.getXDirAdj());
      if(!Objects.equals(prior.getUnicode(),p.getUnicode()) && overlap>Math.min(p.getWidthDirAdj(),prior.getWidthDirAdj())*.7
          && Math.abs(p.getYDirAdj()-prior.getYDirAdj())<Math.max(p.getHeightDir(),prior.getHeightDir())*.3) {
        overlapping=true;words.add(new Word("",0,0,Math.round(p.getXDirAdj()*10),Math.round((p.getYDirAdj()-p.getHeightDir())*10),
            Math.max(1,Math.round(p.getWidthDirAdj()*10)),Math.max(1,Math.round(p.getHeightDir()*10)),0,false));break;
      }
    }
    glyphs.add(p);
    if(bounds==null)rows.put(row,new double[]{x,end});
    else {if(x-bounds[1]>60 || bounds[0]-end>60)columns=true;bounds[0]=Math.min(bounds[0],x);bounds[1]=Math.max(bounds[1],end);}
    super.processTextPosition(p);
  }
  @Override protected void writeString(String text,List<TextPosition> positions) throws IOException {
    int base=writer.getBuffer().length(),cursor=0;Word pending=null;
    for(var p:positions) {
      String raw=p.getUnicode();if(raw==null || raw.isBlank()) continue;
      String normalized=java.text.Normalizer.normalize(raw,java.text.Normalizer.Form.NFKC);
      int at=text.indexOf(normalized,cursor);
      if(at<0) {
        unmapped++;words.add(new Word("",base,base,Math.round(p.getXDirAdj()*10),Math.round((p.getYDirAdj()-p.getHeightDir())*10),
            Math.max(1,Math.round(p.getWidthDirAdj()*10)),Math.max(1,Math.round(p.getHeightDir()*10)),0,false));continue;
      }
      int left=Math.round(p.getXDirAdj()*10),top=Math.round((p.getYDirAdj()-p.getHeightDir())*10);
      int width=Math.max(1,Math.round(p.getWidthDirAdj()*10)),height=Math.max(1,Math.round(p.getHeightDir()*10));
      var w=new Word(text.substring(at,at+normalized.length()),base+at,base+at+normalized.length(),left,top,width,height,100,visibility.getOrDefault(p,false));
      boolean join=pending!=null && pending.end()==w.start() && pending.visible()==w.visible()
          && Math.abs(pending.top()-w.top())<Math.max(pending.height(),w.height())*.6
          && w.left()>=pending.left()+pending.width()-Math.max(2,w.width()*.15)
          && w.left()-pending.left()-pending.width()<Math.max(20,height*.6);
      if(join) pending=new Word(pending.text()+w.text(),pending.start(),w.end(),pending.left(),Math.min(pending.top(),w.top()),
          w.left()+w.width()-pending.left(),Math.max(pending.height(),w.height()),100,w.visible());
      else {if(pending!=null)words.add(pending);pending=w;}
      cursor=at+normalized.length();
    }
    if(pending!=null)words.add(pending);
    super.writeString(text,positions);
  }
  static final class BudgetExceeded extends RuntimeException {}
}
