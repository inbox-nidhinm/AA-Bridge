"""Tidy the static fonts after overlaps are merged: join pieces the build's
merge left separate although they share an edge exactly, and drop segments
shorter than 2 units (1-unit jogs left where two overlapping pieces now
cross a unit away from a node), letting the outline run on from the point
before.

usage: cleanstatic.py FONT.otf [FONT.otf ...]     (rewritten in place)

Only glyphs that have such a segment are rewritten, and a contour is never
left with fewer than three segments.
"""
import math
import sys

import pathops
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont

LIMIT = 2.0


def tidy(ops):
    """the recording with short line segments dropped"""
    out, changed = [], 0
    contour = []

    def flush():
        nonlocal changed
        if not contour:
            return
        start = contour[0][1][0]
        kept = [contour[0]]
        prev = start
        body = contour[1:-1]
        dropped = 0
        for op, args in body:
            end = args[-1]
            # a segment whose ends are under 2 units apart: let the outline
            # run on from the point before (a shift of at most 2 units)
            if math.dist(prev, end) < LIMIT and len(body) - dropped > 3:
                dropped += 1
                continue
            kept.append((op, args))
            prev = end
        # the closing stretch back to the start can be the short one too
        if 0 < math.dist(prev, start) < LIMIT and len(kept) > 3:
            op, args = kept[-1]
            if op == 'lineTo':
                kept.pop()
            else:
                kept[-1] = (op, tuple(args[:-1]) + (start,))
            dropped += 1
        changed += dropped
        kept.append(contour[-1])
        out.extend(kept)

    for op, args in ops:
        contour.append((op, args))
        if op in ('closePath', 'endPath'):
            flush()
            contour = []
    flush()
    return out, changed


def main():
    for path in sys.argv[1:]:
        tt = TTFont(path)
        cff = tt['CFF '].cff
        top = cff.topDictIndex[0]
        cs = top.CharStrings
        gs = tt.getGlyphSet()
        fixed = 0
        for name in tt.getGlyphOrder():
            rp = RecordingPen()
            gs[name].draw(rp)
            # pieces that only touch along an exactly shared edge can come
            # out of the build's overlap merge as separate contours: merge
            # once more, and keep that only where it really joins them
            p = pathops.Path()
            gs[name].draw(p.getPen(glyphSet=gs))
            count = len(list(p.contours))
            p.simplify(fix_winding=True, keep_starting_points=True)
            merged = len(list(p.contours)) < count
            if merged:
                rp = RecordingPen()
                p.draw(rp)
            ops, n = tidy(rp.value)
            if not n and not merged:
                continue
            for _ in range(4):                 # dropping one can leave a neighbour short
                ops, more = tidy(ops)
                if not more:
                    break
            # CFF stores a glyph's width relative to nominalWidthX, and leaves
            # it out when it equals defaultWidthX
            width = tt['hmtx'][name][0]
            priv = top.Private
            pen = T2CharStringPen(None if width == priv.defaultWidthX else width - priv.nominalWidthX, gs)
            for op, args in ops:
                getattr(pen, op)(*args)
            c = pen.getCharString(private=top.Private, globalSubrs=cff.GlobalSubrs)
            cs[name] = c
            fixed += 1
        tt.save(path)
        print(path.split('/')[-1], 'glyphs tidied:', fixed)


if __name__ == '__main__':
    main()
