"""Little steps in the static fonts, where overlaps are already merged.

usage: check_static.py ORIGINAL_DIR TALL_DIR

For each static OTF in TALL_DIR (AABridgeSlabTall-*.otf, AABridgeSlabTall16pt-*)
and its AA Bridge Slab counterpart in ORIGINAL_DIR, count per glyph the
outline segments shorter than 2 units and the on-curve points. Lists the
glyphs that gained short segments, with where they are.
"""
import glob
import math
import os
import sys

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont


def shorts(gs, name):
    rp = RecordingPen()
    gs[name].draw(rp)
    out, prev, start = [], None, None
    for op, args in rp.value:
        if op == 'moveTo':
            prev = start = args[0]
            continue
        if op in ('closePath', 'endPath'):
            if prev and start and 0 < math.dist(prev, start) < 2:
                out.append((prev, start))
            continue
        end = args[-1]
        if prev is not None and math.dist(prev, end) < 2:
            out.append((prev, end))
        prev = end
    return out


def main():
    odir, tdir = sys.argv[1:3]
    total = 0
    for tpath in sorted(glob.glob(os.path.join(tdir, 'AABridgeSlabTall*.otf'))):
        opath = os.path.join(odir, os.path.basename(tpath).replace('AABridgeSlabTall', 'AABridgeSlab'))
        to, tt = TTFont(opath), TTFont(tpath)
        go, gt = to.getGlyphSet(), tt.getGlyphSet()
        gained = []
        for name in tt.getGlyphOrder():
            if name not in go:
                continue
            a, b = shorts(go, name), shorts(gt, name)
            if len(b) > len(a):
                gained.append((name, len(a), len(b), b[:2]))
        total += len(gained)
        print(f'{os.path.basename(tpath):34} glyphs with added short segments: {len(gained)}')
        for name, a, b, where in gained[:12]:
            print(f'    {name:18} {a} -> {b}  e.g. {[(tuple(map(round, p)), tuple(map(round, q))) for p, q in where]}')
    print('total', total)


if __name__ == '__main__':
    main()
