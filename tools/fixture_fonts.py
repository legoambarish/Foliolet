"""Fonts for fictional fixtures only; no font files are copied or distributed."""
import os
from pathlib import Path
from PIL import ImageFont


def fixture_font(size: int, *, bold: bool = False):
    """Fail explicitly rather than silently changing a labelled corpus to a bitmap font."""
    override = os.environ.get('FOLIOLET_TEST_FONT_BOLD' if bold else 'FOLIOLET_TEST_FONT')
    names = ([override] if override else []) + [
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
    ]
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    raise RuntimeError('Install DejaVu Sans or set FOLIOLET_TEST_FONT and FOLIOLET_TEST_FONT_BOLD.')
