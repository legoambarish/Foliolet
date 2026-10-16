"""Download only public CORD samples; never uploads user documents.

CORD: Consolidated Receipt Dataset for Post-OCR Parsing, NAVER CLOVA / CORD
contributors. Source dataset and images: CC BY 4.0. Preserve attribution and
unmodified source annotations. Losslessly embed each image in a PDF at 150 dpi.
This is a receipt generalization stress test, not an Indian academic benchmark.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import requests
import fitz
from PIL import Image
import io

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'.local-data/ps32-cord'
DATASET = 'naver-clova-ix/cord-v2'
# Selection frozen before any Foliolet output; train is calibration, test held out.
SELECTION = {'train': [0, 10], 'test': [0, 7, 14, 21, 28, 35]}


def download(url, limit=12*1024*1024):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not (parsed.hostname == 'huggingface.co' or parsed.hostname.endswith('.huggingface.co')):
        raise ValueError('Only the official public dataset host is permitted')
    with requests.get(url, timeout=(10,60), stream=True) as response:
        response.raise_for_status()
        data = bytearray()
        for part in response.iter_content(65536):
            if len(data)+len(part)>limit: raise ValueError('Public sample exceeds download limit')
            data.extend(part)
        return bytes(data)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(download('https://huggingface.co/api/datasets/'+DATASET))
    revision = metadata['sha']
    manifest, failures = [], []
    for split, indexes in SELECTION.items():
        for index in indexes:
            identifier = f'cord-{split}-{index:03d}'
            try:
                url = f'https://datasets-server.huggingface.co/rows?dataset={DATASET}&config=default&split={split}&offset={index}&length=1'
                response = json.loads(download(url))
                row = response['rows'][0]['row']
                annotation_text = row['ground_truth']
                annotation = json.loads(annotation_text)
                image = download(row['image']['src'])
                source = OUT/(identifier+'.png')
                # Retain the source bytes with an honest extension from actual encoding.
                original_image = Image.open(io.BytesIO(image))
                source = source.with_suffix('.jpg' if original_image.format == 'JPEG' else '.png')
                source.write_bytes(image)
                (OUT/(identifier+'.ground-truth.json')).write_text(json.dumps(annotation,indent=2))
                width, height = original_image.size
                document = fitz.open(); page = document.new_page(width=width*72/150, height=height*72/150)
                page.insert_image(page.rect, stream=image)
                pdf = OUT/(identifier+'.pdf'); document.save(pdf); document.close()
                record = dict(id=identifier,file=str(pdf.relative_to(ROOT)),fictional=False,
                    category='public-real-receipt',split='calibration' if split=='train' else 'held-out',
                    license='CC-BY-4.0',dataset=DATASET,datasetRevision=revision,datasetSplit=split,rowIndex=index,
                    sourceImage=source.name,sourceSha256=hashlib.sha256(image).hexdigest(),
                    pdfSha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                    annotationSha256=hashlib.sha256(annotation_text.encode()).hexdigest(),expected={},
                    groundTruth='Original dataset human annotation retained; no academic field-schema accuracy inferred',
                    conversion='Original image bytes embedded without resampling; PDF page uses 150 dpi physical scale')
                manifest.append(record)
                print(identifier,'downloaded',width,height,flush=True)
            except Exception as error:
                failures.append({'id':identifier,'error':type(error).__name__+': '+str(error)[:300]})
    (OUT/'cases.json').write_text(json.dumps(manifest,indent=2))
    (OUT/'download-failures.json').write_text(json.dumps(failures,indent=2))
    (OUT/'ATTRIBUTION.md').write_text(
        '# CORD public evaluation samples\n\n'
        'CORD: Consolidated Receipt Dataset for Post-OCR Parsing, NAVER CLOVA and CORD contributors.\n\n'
        'Dataset: https://huggingface.co/datasets/naver-clova-ix/cord-v2\n'
        'Original project: https://github.com/clovaai/cord\n'
        'License: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/\n\n'
        'Source image and annotation bytes originate from the public dataset. PDF wrapping changes only physical page scale; '
        'source pixels and source annotations are not corrected. Dataset revision: `'+revision+'`.\n\n'
        'Two training rows are calibration-only. Six separately selected test rows are held out. '
        'Samples do not establish accuracy on Indian academic credentials. Privacy review is required before public presentation.\n')
    if len(manifest)!=8: raise SystemExit('Incomplete public corpus; inspect download-failures.json')

if __name__ == '__main__': main()
