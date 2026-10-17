package com.sih26190.dms.foli;

import java.awt.*;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;

/** Local visual matching of the supplied public branding, never issuer authentication. */
final class BrandingTemplate {
  private static final int W=120,H=50;
  private static final boolean[] TEMPLATE=loadImage();
  private static boolean[] loadImage() {
    try(var in=BrandingTemplate.class.getResourceAsStream("/indicators/digilocker-brand.png")) {
      var image=ImageIO.read(in);return mask(image,0,0,image.getWidth(),image.getHeight());
    }catch(Exception e){return null;}
  }
  private static boolean ink(int rgb) {
    int r=rgb>>16&255,g=rgb>>8&255,b=rgb&255;
    return (r>g*1.2 && b>g*1.2 && b>60 && r<235) || (Math.max(r,Math.max(g,b))-Math.min(r,Math.min(g,b))<35 && r<170);
  }
  private static boolean[] mask(BufferedImage image,int left,int top,int width,int height) {
    boolean[] out=new boolean[W*H];
    for(int y=0;y<H;y++)for(int x=0;x<W;x++)
      out[y*W+x]=ink(image.getRGB(left+Math.min(width-1,(int)((x+.5)*width/W)),top+Math.min(height-1,(int)((y+.5)*height/H))));
    return out;
  }
  static IntakeIndicators.Logo match(BufferedImage image) {
    if(TEMPLATE==null)return new IntakeIndicators.Logo(false,0,"Branding template unavailable");
    double scale=Math.min(1,1600d/Math.max(image.getWidth(),image.getHeight()));
    var frame=new BufferedImage(Math.max(1,(int)(image.getWidth()*scale)),Math.max(1,(int)(image.getHeight()*scale)),BufferedImage.TYPE_INT_RGB);
    var g=frame.createGraphics();g.setColor(Color.WHITE);g.fillRect(0,0,frame.getWidth(),frame.getHeight());g.drawImage(image,0,0,frame.getWidth(),frame.getHeight(),null);g.dispose();
    try {
      for(int angle=0;angle<4;angle++) {
        int w=frame.getWidth(),h=frame.getHeight();byte[] pixels=new byte[w*h];int[] queue=new int[w*h];
        for(int y=0;y<h;y++)for(int x=0;x<w;x++)if(ink(frame.getRGB(x,y)))pixels[y*w+x]=1;
        for(int origin=0;origin<pixels.length;origin++) {
          if(pixels[origin]!=1)continue;
          int count=1,read=0,left=origin%w,right=left,top=origin/w,bottom=top;queue[0]=origin;pixels[origin]=2;
          while(read<count) {
            int p=queue[read++],x=p%w,y=p/w;left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);
            for(int q:new int[]{x>0?p-1:-1,x+1<w?p+1:-1,y>0?p-w:-1,y+1<h?p+w:-1})
              if(q>=0 && pixels[q]==1){pixels[q]=2;queue[count++]=q;}
          }
          int cw=right-left+1,ch=bottom-top+1;
          if(ch<20 || cw<ch*2.1 || cw>ch*2.8 || count<cw*ch*.25 || count>cw*ch*.85)continue;
          var candidate=mask(frame,left,top,cw,ch);int union=0,intersection=0,letters=0,matched=0;
          for(int y=0;y<H;y++)for(int x=0;x<W;x++) {
            int p=y*W+x;if(candidate[p]||TEMPLATE[p])union++;if(candidate[p]&&TEMPLATE[p])intersection++;
            // The white wordmark inside the filled block is required independently of the silhouette.
            if(x>W*.44 && x<W*.94 && y>H*.37 && y<H*.73 && !TEMPLATE[p]){letters++;if(!candidate[p])matched++;}
          }
          double score=union==0?0:(double)intersection/union;
          if(score>=.86 && letters>30 && (double)matched/letters>=.72)
            return new IntakeIndicators.Logo(true,score,"Matching ring, document graphic and wordmark pixels; branding only");
        }
        var next=new BufferedImage(h,w,BufferedImage.TYPE_INT_RGB);var rg=next.createGraphics();rg.translate(h,0);rg.rotate(Math.PI/2);rg.drawImage(frame,0,0,null);rg.dispose();frame.flush();frame=next;
      }
      return new IntakeIndicators.Logo(false,0,"No matching complete branding template");
    }finally{frame.flush();}
  }
}
