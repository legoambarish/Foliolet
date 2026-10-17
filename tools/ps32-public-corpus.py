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
import time
import requests
import fitz
from PIL import Image
import io

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'.local-data/ps32-cord'
DATASET = 'naver-clova-ix/cord-v2'
# Frozen before any Foliolet output; never replace failing rows with easier ones.
SELECTION = {'train': [0, 10], 'test': [0, 7, 14, 21, 28, 35]}


def download(url, limit=12*1024*1024):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or not (parsed.hostname == 'huggingface.co' or parsed.hostname.endswith('.huggingface.co')):
        raise ValueError('Only the official public dataset host is permitted')
    for attempt in range(4):
        try:
            with requests.get(url, timeout=(10,60), stream=True) as response:
                response.raise_for_status()
                data = bytearray()
                for part in response.iter_content(65536):
                    if len(data)+len(part)>limit: raise ValueError('Public sample exceeds download limit')
                    data.extend(part)
                return bytes(data)
        except requests.RequestException:
            if attempt == 3: raise
            time.sleep(.5 * (2**attempt))


def row_for(split, index):
    base = f'https://datasets-server.huggingface.co/'
    query = f'dataset={DATASET}&config=default&split={split}'
    try:
        rows = json.loads(download(base+'rows?'+query+f'&offset={index}&length=1'))['rows']
    except requests.RequestException:
        # Same frozen row from the provider's cached viewer endpoint, not a substitute sample.
        rows = json.loads(download(base+'first-rows?'+query))['rows']
    for row in rows:
        if row.get('row_idx') == index: return row['row']
    raise ValueError('Provider did not return the exact requested row')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    revision = json.loads(download('https://huggingface.co/api/datasets/'+DATASET))['sha']
    manifest, failures = [], []
    for split, indexes in SELECTION.items():
        for index in indexes:
            identifier = f'cord-{split}-{index:03d}'
            try:
                row = row_for(split,index)
                annotation_text = row['ground_truth']; annotation = json.loads(annotation_text)
                image = download(row['image']['src'])
                original_image = Image.open(io.BytesIO(image))
                source = OUT/(identifier+('.jpg' if original_image.format == 'JPEG' else '.png'))
                source.write_bytes(image)
                (OUT/(identifier+'.ground-truth.json')).write_text(json.dumps(annotation,indent=2))
                width, height = original_image.size
                document = fitz.open(); page = document.new_page(width=width*72/150, height=height*72/150)
                page.insert_image(page.rect, stream=image)
                pdf = OUT/(identifier+'.pdf'); document.save(pdf); document.close()
                manifest.append(dict(id=identifier,file=str(pdf.relative_to(ROOT)),fictional=False,
                    category='public-real-receipt',split='calibration' if split=='train' else 'held-out',
                    license='CC-BY-4.0',dataset=DATASET,datasetRevision=revision,datasetSplit=split,rowIndex=index,
                    sourceImage=source.name,sourceSha256=hashlib.sha256(image).hexdigest(),
                    pdfSha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                    annotationSha256=hashlib.sha256(annotation_text.encode()).hexdigest(),expected={},
                    groundTruth='Original dataset human annotation retained; no academic field-schema accuracy inferred',
                    conversion='Original image bytes embedded without resampling; PDF page uses 150 dpi physical scale'))
                print(identifier,'downloaded',width,height,flush=True)
            except Exception as error:
                failures.append({'id':identifier,'error':type(error).__name__+': '+str(error)[:300]})
    current = json.loads(download('https://huggingface.co/api/datasets/'+DATASET))['sha']
    if current != revision: failures.append({'id':'revision','error':'Dataset revision changed during acquisition'})
    (OUT/'cases.json').write_text(json.dumps(manifest,indent=2))
    (OUT/'download-failures.json').write_text(json.dumps(failures,indent=2))
    (OUT/'ATTRIBUTION.md').write_text(
        '# CORD public evaluation samples\n\n'
        'CORD: Consolidated Receipt Dataset for Post-OCR Parsing, NAVER CLOVA and CORD contributors.\n\n'
        'Dataset: https://huggingface.co/datasets/naver-clova-ix/cord-v2\n'
        'Original project: https://github.com/clovaai/cord\n'
        'License: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/\n\n'
        'PDF wrapping changes only physical page scale; source pixels and annotations are not corrected. '
        'Dataset revision: `'+revision+'`.\n\n'
        'Two training rows are calibration-only. Six separately selected test rows are held out. '
        'Samples do not establish accuracy on Indian academic credentials. Privacy review precedes public presentation.\n')
    if len(manifest)!=8 or failures: raise SystemExit('Incomplete public corpus; inspect download-failures.json')

if __name__ == '__main__': main()
