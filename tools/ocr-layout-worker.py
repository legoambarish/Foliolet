"""Bounded, offline CPU OCR worker. Only the parent reader supplies local PNG paths.

The three bundled models are pinned separately from the Python package. No model
discovery/download, URLs, shell commands, or remote inference are permitted.
"""
import argparse
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys

MODELS = {
    'PP-OCRv6_det_small.onnx': '090f04abcd9d9a7498bc4ebf677e4cb9bdce1fe4197ddb7e529f1ef44e1ff94f',
    'PP-OCRv6_rec_small.onnx': '6f327246b50388f3c176ae304bd95767ea6dc0c9ae92153ef8cbe210b3c14884',
    'ch_ppocr_mobile_v2.0_cls_mobile.onnx': 'e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c',
}


def deny_network(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.bind', 'socket.getaddrinfo'):
        raise PermissionError('Networking is disabled in the local OCR worker')


def models():
    if importlib.metadata.version('rapidocr') != '3.10.0' or importlib.metadata.version('onnxruntime') != '1.31.0':
        raise RuntimeError('Unexpected OCR runtime version')
    root = Path(importlib.util.find_spec('rapidocr').origin).parent / 'models'
    for name, expected in MODELS.items():
        source = root / name
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Local OCR model missing or altered')
    return root


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    sys.addaudithook(deny_network)
    os.environ.update(OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2')
    root = models()
    if args.check:
        print(json.dumps({'ready': True, 'modelBytes': sum((root / n).stat().st_size for n in MODELS)}))
        return
    if not args.input or not args.output or args.input.suffix.lower() != '.png' or args.input.stat().st_size > 40_000_000:
        raise ValueError('Expected a bounded local PNG and output path')
    from PIL import Image
    with Image.open(args.input) as image:
        width, height = image.size
        if width < 1 or height < 1 or width * height > 8_000_000:
            raise ValueError('OCR image exceeds pixel budget')
        image.load()
    import onnxruntime
    onnxruntime.disable_telemetry_events()
    from rapidocr import RapidOCR
    params = {
        'Global.log_level': 'error', 'Global.return_word_box': True,
        'EngineConfig.onnxruntime.intra_op_num_threads': 2,
        'EngineConfig.onnxruntime.inter_op_num_threads': 2,
        'EngineConfig.onnxruntime.use_cuda': False,
        'EngineConfig.onnxruntime.use_dml': False,
        'Det.model_path': str(root / 'PP-OCRv6_det_small.onnx'),
        'Rec.model_path': str(root / 'PP-OCRv6_rec_small.onnx'),
        'Cls.model_path': str(root / 'ch_ppocr_mobile_v2.0_cls_mobile.onnx'),
    }
    with contextlib.redirect_stdout(sys.stderr):
        result = RapidOCR(params=params)(str(args.input), return_word_box=True)
    text, words = '', []
    for line in result.word_results or ():
        if not isinstance(line, (list, tuple)):
            continue
        for word in line:
            if len(word) != 3 or word[2] is None or len(words) >= 2048:
                continue
            value, confidence, box = word
            value = str(value).strip()
            if not value or len(value) > 500 or len(text) + len(value) > 100_000:
                continue
            xs, ys = [float(p[0]) for p in box], [float(p[1]) for p in box]
            left, top = max(0, int(min(xs))), max(0, int(min(ys)))
            right, bottom = min(width, int(max(xs)) + 1), min(height, int(max(ys)) + 1)
            if right <= left or bottom <= top:
                continue
            if text:
                text += ' '
            start = len(text.encode('utf-16-le')) // 2
            text += value
            words.append(dict(text=value, start=start, end=len(text.encode('utf-16-le')) // 2, left=left, top=top,
                              width=right-left, height=bottom-top, confidence=max(0, min(100, float(confidence)*100))))
        text += '\n' if text else ''
    payload = dict(text=text.rstrip(), words=words, width=width, height=height,
                   method='rapidocr-3.10.0-ppocrv6-small-cpu', modelHashes=MODELS)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding='utf8')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never put source text, local document names or library exceptions in logs.
        print('Local layout OCR unavailable or failed its integrity checks.', file=sys.stderr)
        sys.exit(2)
