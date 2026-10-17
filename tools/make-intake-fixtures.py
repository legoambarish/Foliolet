"""Locally generated synthetic fixtures, never genuine issued documents/QR data."""
import io
import json
import os
from pathlib import Path
import subprocess
import fitz
from fixture_fonts import fixture_font
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data/intake-tests/fixtures'


def qr(payload):
    code = "const q=require('qrcode-generator')(0,'M');q.addData(process.argv[1]);q.make();console.log(JSON.stringify(Array.from({length:q.getModuleCount()},(_,r)=>Array.from({length:q.getModuleCount()},(_,c)=>q.isDark(r,c)))));"
    bits = json.loads(subprocess.check_output(['node', '-e', code, payload], text=True))
    unit, margin = 6, 4
    image = Image.new('RGB', ((len(bits)+margin*2)*unit,)*2, 'white')
    draw = ImageDraw.Draw(image)
    for y, row in enumerate(bits):
        for x, dark in enumerate(row):
            if dark: draw.rectangle(((x+margin)*unit, (y+margin)*unit, (x+margin+1)*unit-1, (y+margin+1)*unit-1), fill='black')
    return image


def graphic():
    image = Image.new('RGB', (680, 240), 'white')
    draw = ImageDraw.Draw(image)
    purple = (110, 55, 230)
    draw.rounded_rectangle((100, 45, 660, 200), 22, fill=purple)
    draw.ellipse((10, 10, 230, 230), fill=purple)
    draw.ellipse((25, 25, 215, 215), fill='white')
    draw.rounded_rectangle((70, 65, 160, 173), 8, fill=purple)
    draw.polygon(((130, 65), (160, 95), (130, 95)), fill='white')
    draw.text((260, 65), 'Powered by', font=fixture_font(28), fill='white')
    draw.text((255, 112), 'DigiLocker', font=fixture_font(54, bold=True), fill='white')
    return image


def png(image):
    output = io.BytesIO(); image.save(output, format='PNG'); return output.getvalue()


def native(name, brand=False, code=None, pages=1, scanned=False, hybrid=False):
    document = fitz.open()
    for number in range(pages):
        page = document.new_page()
        page.insert_text((60, 70), 'SYNTHETIC TEST DOCUMENT - no issuer verification', fontsize=13)
        page.insert_text((60, 105), 'Name: Synthetic Student', fontsize=14)
        page.insert_text((60, 140), 'Math: 90', fontsize=16)
        page.insert_text((60, 175), 'Science: 80', fontsize=16)
        page.insert_text((60, 210), 'CGPA: unavailable', fontsize=14)
        page.insert_text((60, 245), 'Cancellation: No renewal fee unless notice is late.', fontsize=12)
        page.insert_text((60, 270), 'Late fee: INR 9300 after 30 days.', fontsize=12)
        if number == pages-1:
            if code: page.insert_image(fitz.Rect(60, 510, 240, 690), stream=png(qr(code)))
            if brand: page.insert_image(fitz.Rect(280, 525, 550, 625), stream=png(graphic()))
    if hybrid:
        image = Image.new('RGB', (1000, 100), 'white'); draw = ImageDraw.Draw(image)
        draw.text((30, 15), 'Extra charge: INR 800 for dispatch', font=fixture_font(32), fill='black')
        document[0].insert_image(fitz.Rect(60, 330, 540, 380), stream=png(image))
    if scanned:
        raster = fitz.open()
        for page in document:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            output = raster.new_page(width=page.rect.width, height=page.rect.height)
            output.insert_image(output.rect, stream=pix.tobytes('png'))
        document.close(); document = raster
    document.save(OUT / name)
    document.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    official = 'https://verify.digilocker.gov.in/synthetic-no-issuer-verification'
    native('both.pdf', True, official)
    native('logo-only.pdf', True)
    native('qr-only.pdf', code=official)
    native('neither.pdf')
    with fitz.open() as table:
        page=table.new_page();page.insert_text((50,60),'SYNTHETIC TABLE - NOT ISSUED',fontsize=14)
        for row,(label,score) in enumerate([('Subject','Marks'),('Math','90'),('Science','80'),('English','85')]):
            y=120+row*35;page.insert_text((60,y),label,fontsize=14);page.insert_text((300,y),score,fontsize=14)
            page.draw_line((50,y+8),(400,y+8))
        table.save(OUT/'table.pdf')
    native('unrelated-qr.pdf', code='https://example.com/synthetic')
    native('scanned.pdf', True, official, scanned=True)
    native('hybrid.pdf', True, official, hybrid=True)
    native('last-page.pdf', code=official, pages=3)
    native('encrypted.pdf')
    with fitz.open(OUT / 'encrypted.pdf') as source:
        source.save(OUT / 'protected.pdf', encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw='synthetic-owner', user_pw='synthetic-reader')
    (OUT / 'malformed.pdf').write_bytes(b'%PDF-1.7\nmalformed test only\n%%EOF')
    (OUT / 'marks.txt').write_text('Math: 90\nScience: 80\nName: Synthetic Student\nCGPA: unavailable\n', encoding='utf-8')
    (OUT / 'unsupported.docx').write_bytes(b'Synthetic unsupported bytes')
    print('Generated synthetic fixtures in this worktree only. No reference QR payload was copied.', flush=True)


if __name__ == '__main__': main()
