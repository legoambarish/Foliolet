"""Bounded offline complementary decoder. stdout is private IPC, never a log.

Does not follow QR URLs, decrypt payloads, contact issuers or assert authenticity.
"""
import json
import sys
from PIL import Image
import zxingcpp

Image.MAX_IMAGE_PIXELS = 8_000_000
with Image.open(sys.argv[1]) as image:
    if image.width * image.height > 8_000_000:
        raise ValueError('Pixel budget exceeded')
    results = zxingcpp.read_barcodes(image, formats=zxingcpp.BarcodeFormat.QRCode)
    out = []
    for result in results[:16]:
        if not result.valid or len(result.text) > 4096:
            continue
        p = result.position
        points = [p.top_left, p.top_right, p.bottom_right, p.bottom_left]
        out.append({'text': result.text, 'left': min(p.x for p in points),
                    'top': min(p.y for p in points), 'right': max(p.x for p in points),
                    'bottom': max(p.y for p in points)})
    print(json.dumps(out, ensure_ascii=True))
