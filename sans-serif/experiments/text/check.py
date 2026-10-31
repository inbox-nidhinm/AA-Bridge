"""Stroke checks for the text cut test fonts: the thickest stroke crossing a
chosen height in letters with spines and diagonals, as a share of the n stem.
Anything well over 1.0 reads darker than the stems in text.

usage (from the repo root): python sans-serif/experiments/text/check.py
"""
import glob
import os
import sys

from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from textcut import measure, strokes  # noqa: E402

# letter: height (share of the glyph's height) at which to cross its strokes
AT = {'S': 0.5, 's': 0.5, '2': 0.3, 'z': 0.5, 'Z': 0.5, '7': 0.4, 'A': 0.3,
      'V': 0.5, 'N': 0.5, 'v': 0.5, 'w': 0.5, 'k': 0.3, 'x': 0.25, 'e': 0.55, 'a': 0.3}

paths = sorted(glob.glob(os.path.join(HERE, 'fonts', '*.ttf')))

if '--sweep' in sys.argv:
    # every letter and figure, crossed at 11 heights: flag strokes that got
    # darker than the stem in the test font when they were not before
    before = TTFont(os.path.join(HERE, 'fonts', 'AABridgeSansTextBefore-Regular.ttf'))
    test = TTFont(os.path.join(HERE, 'fonts', sys.argv[sys.argv.index('--sweep') + 1]))
    sb, st = measure(before)['stem'], measure(test)['stem']
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$&@%'
    for c in chars:
        worst = None
        for i in range(11):
            h = 0.2 + i * 0.06
            try:
                rb = max(strokes(before, c, h)) / sb
                rt = max(strokes(test, c, h)) / st
            except ValueError:
                continue
            if rt > 1.12 and rt - rb > 0.1 and (worst is None or rt > worst[1]):
                worst = (h, rt, rb)
        if worst:
            print(f'{c}: {worst[1]:.2f} of stem at {worst[0]:.2f} height (before {worst[2]:.2f})')
    sys.exit()

print(f"{'font':8}{'stem':>6}{'o top':>7}" + ''.join(f'{c:>6}' for c in AT))
for p in paths:
    f = TTFont(p)
    m = measure(f)
    st = m['stem']
    tag = os.path.basename(p).replace('AABridgeSansText', '').replace('-Regular.ttf', '')
    vals = [max(strokes(f, c, h)) / st for c, h in AT.items()]
    print(f"{tag:8}{st:6.0f}{m['o_top'] / st:7.2f}" + ''.join(f'{v:6.2f}' for v in vals))
