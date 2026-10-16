"""Reproducible, fictional certificate/table fixtures. Real vault samples remain ignored and private."""
import io, json
from pathlib import Path
import fitz
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.local-data/ocr-p0/fixtures'
ROWS=[('CS101','Mathematics','100','91','A+'),('PH102','Physics','100','86','A'),
      ('CH103','Chemistry','100','78','B+'),('EN104','English','100','84','A'),('CS105','Computer Science','100','93','A+')]

def write(page,x,y,text,size=11): page.insert_text((x,y),text,fontsize=size,fontname='hebo' if size>15 else 'helv')
def base():
    d=fitz.open();p=d.new_page(width=595,height=842)
    write(p,52,52,'NORTH VALLEY INSTITUTE OF TECHNOLOGY',17)
    write(p,155,77,'SEMESTER GRADE REPORT',14)
    write(p,48,110,'FICTIONAL BENCHMARK - NO ISSUER AUTHORITY',9)
    return d,p
def table(p,tiny=False,ambiguous=False,confused=False):
    size=5.5 if tiny else 11; xs=[45,120,320,395,505];top=260
    for x,t in zip(xs,['Code','Subject','Max Marks','Marks Obtained','Grade']):write(p,x,top,t,9 if not tiny else size)
    for i,row in enumerate(ROWS):
        y=top+34*(i+1)
        for x,t in zip(xs,row): write(p,x,y,('9O' if confused and t=='91' else t),size)
        p.draw_line((40,y+12),(555,y+12),color=(.7,.7,.7),width=.4)
    if ambiguous:
        write(p,395,top+34,'71',size);write(p,395,top+68,'68',size)
def finish(d,name):d.save(OUT/name);d.close()
def raster(source,name,rotation=0,noise=False):
    d=fitz.open(OUT/source);o=fitz.open()
    for p in d:
        pix=p.get_pixmap(matrix=fitz.Matrix(2.5,2.5));im=Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
        if rotation:im=im.rotate(rotation,expand=True,fillcolor='white')
        if noise:im=im.filter(ImageFilter.GaussianBlur(.8))
        buf=io.BytesIO();im.save(buf,format='PNG');q=o.new_page(width=im.width/2.5,height=im.height/2.5);q.insert_image(q.rect,stream=buf.getvalue())
    finish(o,name);d.close()
def cases():
    table_truth={}
    for _,subject,maximum,mark,grade in ROWS:
        slug=subject.lower().replace(' ','_')
        table_truth['education.math' if subject=='Mathematics' else 'extracted.'+slug+'_marks']=mark
        table_truth['extracted.'+slug+'_maximum_marks']=maximum
        table_truth['extracted.'+slug+'_grade']=grade
    identity={'person.name':'Ananya Rao','person.birth_date':'2004-07-14','extracted.enrollment_number':'NV202600417','education.cgpa':'8.67'}
    result=[]
    for p in sorted(OUT.glob('*.pdf')):
        expected=dict(table_truth,**identity)
        if p.name=='tiny-table.pdf':expected=dict(table_truth)
        if p.name=='ambiguous-table.pdf':expected={k:v for k,v in table_truth.items() if k not in ('education.math','extracted.physics_marks')}
        if p.name in ('ocr-confusions.pdf','ocr-confusions-scan.pdf'):expected=dict(table_truth,**{'education.math':'9O'})
        if p.name=='native-columns.pdf':expected={'person.name':'Ananya Rao','person.birth_date':'2004-07-14','education.cgpa':'8.67','education.course':'B.Tech','extracted.year':'2026','education.institution':'North Valley'}
        if p.name=='native-adjacent.pdf':expected={k:identity[k] for k in ('person.name','extracted.enrollment_number','education.cgpa')}
        if p.name=='form-widgets.pdf':expected={k:identity[k] for k in ('person.name','person.birth_date','education.cgpa')}
        if p.name in ('mixed-values.pdf','native-hidden.pdf'):expected={'person.name':'Ananya Rao','extracted.physics':'86'}
        result.append({'id':p.stem,'file':str(p.relative_to(ROOT)),'expected':expected,'fictional':True})
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    d,p=base();write(p,45,145,'Student Name');write(p,190,145,'Ananya Rao');write(p,45,177,'Enrollment Number');write(p,190,177,'NV202600417')
    write(p,45,209,'Date of Birth');write(p,190,209,'14 July 2004');table(p);write(p,45,535,'CGPA');write(p,190,535,'8.67');finish(d,'native-table.pdf')
    raster('native-table.pdf','scan-table.pdf');raster('native-table.pdf','scan-rotated90.pdf',90);raster('native-table.pdf','scan-rotated180.pdf',180)
    raster('native-table.pdf','scan-noise.pdf',noise=True)
    d,p=base();table(p,tiny=True);finish(d,'tiny-table.pdf')
    d,p=base();table(p,ambiguous=True);finish(d,'ambiguous-table.pdf')
    d,p=base();table(p,confused=True);finish(d,'ocr-confusions.pdf');raster('ocr-confusions.pdf','ocr-confusions-scan.pdf')
    d,p=base()
    for x,items in [(45,[('Name','Ananya Rao'),('Date of Birth','2004-07-14'),('CGPA','8.67')]),(325,[('Course','B.Tech'),('Year','2026'),('Institution','North Valley')])]:
        for i,(k,v) in enumerate(items):write(p,x,160+i*65,k+': '+v,10)
    finish(d,'native-columns.pdf')
    d,p=base()
    for i,(k,v) in enumerate([('Student Name','Ananya Rao'),('Enrollment Number','NV202600417'),('CGPA','8.67')]):
        y=160+i*85;write(p,45,y,k);write(p,45,y+24,v)
    finish(d,'native-adjacent.pdf')
    d,p=base()
    for i,(k,v) in enumerate([('Student Name','Ananya Rao'),('Date of Birth','14/07/2004'),('CGPA','8.67')]):
        y=145+i*60;write(p,45,y+18,k)
        w=fitz.Widget();w.field_name=k;w.field_type=fitz.PDF_WIDGET_TYPE_TEXT;w.field_value=v;w.rect=fitz.Rect(190,y,450,y+28);w.text_fontsize=12;p.add_widget(w)
    finish(d,'form-widgets.pdf')
    d,p=base();write(p,45,150,'Name: Ananya Rao');write(p,45,190,'Mathematics: 91');write(p,45,230,'Physics: 86')
    im=Image.new('RGB',(550,110),'white');g=ImageDraw.Draw(im);g.text((10,10),'Mathematics: 71',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',36),fill='black')
    b=io.BytesIO();im.save(b,format='PNG');p.insert_image(fitz.Rect(40,167,400,208),stream=b.getvalue());finish(d,'mixed-values.pdf')
    d,p=base();write(p,45,150,'Name: Ananya Rao');p.insert_text((45,190),'Mathematics: 99',fontsize=11,render_mode=3)
    write(p,45,230,'Physics: 86');finish(d,'native-hidden.pdf')
    fixtures=cases();(OUT.parent/'cases.json').write_text(json.dumps(fixtures,indent=2),encoding='utf8')
    print('Generated',len(fixtures),'fictional layout cases; originals untouched.')
if __name__=='__main__':main()
