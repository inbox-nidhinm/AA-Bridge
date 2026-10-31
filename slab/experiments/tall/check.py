"""Measure the tall experiment against the original, Regular display.

usage: check.py ORIGINAL.otf BUILD.otf [BUILD.otf ...]

Prints, per font: vertical metrics, stem / hairline / serif thicknesses,
the true (perpendicular) thickness of diagonals and of the S and s spines,
and the contour count of every key letter after overlaps are merged (the
topology test: a broken join or sliver changes the count).
"""
import math
import sys

import pathops
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

KEY = 'HORSAandglovesxpy'


class Font:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.gs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()

    def path(self, ch):
        p = pathops.Path()
        self.gs[self.cmap[ord(ch)]].draw(p.getPen(glyphSet=self.gs))
        p.simplify()
        return p

    def bounds(self, ch):
        b = BoundsPen(self.gs)
        self.gs[self.cmap[ord(ch)]].draw(b)
        return b.bounds

    def width(self, ch):
        return self.gs[self.cmap[ord(ch)]].width

    def runs(self, ch, axis, at):
        """ink runs [(start, length)] along y=at (axis 'h') or x=at ('v')"""
        r = pathops.Path()
        pen = r.getPen()
        if axis == 'h':
            pts = ((-500, at - .5), (2500, at - .5), (2500, at + .5), (-500, at + .5))
        else:
            pts = ((at - .5, -800), (at + .5, -800), (at + .5, 1800), (at - .5, 1800))
        pen.moveTo(pts[0]); [pen.lineTo(p) for p in pts[1:]]; pen.closePath()
        out = []
        for c in pathops.op(self.path(ch), r, pathops.PathOp.INTERSECTION).contours:
            v = [pt[0 if axis == 'h' else 1] for s in c.segments for pt in s[1]]
            out.append((min(v), max(v) - min(v)))
        return sorted(out)


def diagonal(f, ch, which, y0, y1):
    """perpendicular thickness of a diagonal stroke between heights y0..y1:
    horizontal width at the middle times the sine of the stroke angle"""
    def run(y):
        rs = [r for r in f.runs(ch, 'h', y) if r[1] > 20]
        return rs[which]
    ym = (y0 + y1) / 2
    a, b = run(y0), run(y1)
    dx = (b[0] + b[1] / 2) - (a[0] + a[1] / 2)
    sin = (y1 - y0) / math.hypot(dx, y1 - y0)
    return run(ym)[1] * sin


def spine(f, ch):
    """perpendicular thickness of an S spine at the glyph centre, from its
    vertical and horizontal cross-sections: t = 1/sqrt(1/wx^2 + 1/wy^2)"""
    b = f.bounds(ch)
    cx = (b[0] + b[2]) / 2
    v = f.runs(ch, 'v', cx)
    mid = sorted(v, key=lambda r: abs(r[0] + r[1] / 2 - (b[1] + b[3]) / 2))[0]
    cy = mid[0] + mid[1] / 2
    h = sorted(f.runs(ch, 'h', cy), key=lambda r: abs(r[0] + r[1] / 2 - cx))[0]
    return 1 / math.sqrt(1 / h[1] ** 2 + 1 / mid[1] ** 2)


def report(f):
    xh, cap = f.bounds('x')[3], f.bounds('H')[3]
    o = f.bounds('o')
    O = f.bounds('O')
    vo = f.runs('o', 'v', (o[0] + o[2]) / 2)
    vO = f.runs('O', 'v', (O[0] + O[2]) / 2)
    n = f.bounds('n')
    return {
        'x-height': xh, 'cap height': cap, 'ascender (d)': f.bounds('d')[3], 'descender (p)': f.bounds('p')[1],
        'overshoot o / O': f'{o[3] - xh:.0f} / {O[3] - cap:.0f}',
        'stem n': [r for r in f.runs('n', 'h', xh * .45) if r[1] > 20][0][1],
        'stem H': [r for r in f.runs('H', 'h', cap * .3) if r[1] > 20][0][1],
        'o side (thick)': f.runs('o', 'h', (o[1] + o[3]) / 2)[0][1],
        'o top / bottom (thin)': f'{vo[-1][1]:.0f} / {vo[0][1]:.0f}',
        'O top / bottom (thin)': f'{vO[-1][1]:.0f} / {vO[0][1]:.0f}',
        'H bar': f.runs('H', 'v', f.width('H') / 2)[0][1],
        'n foot serif': f.runs('n', 'v', n[0] + 5)[0][1],
        'v thick diagonal': diagonal(f, 'v', 0, xh * .35, xh * .65),
        'A thick diagonal': diagonal(f, 'A', -1, cap * .55, cap * .8),
        'x thick diagonal': diagonal(f, 'x', 0, xh * .62, xh * .8),
        'S spine': spine(f, 'S'),
        's spine': spine(f, 's'),
    }


def contours(f):
    return {ch: len(list(f.path(ch).contours)) for ch in dict.fromkeys(KEY)}


def micro(f, ch, limit=2.0):
    """segments shorter than `limit` units in the merged outline: the little
    steps left where overlapping pieces no longer meet exactly"""
    n = 0
    for c in f.path(ch).contours:
        prev = None
        for op, pts in c.segments:
            if op == 'moveTo':
                prev = pts[0]
                continue
            if op == 'closePath' or not pts:
                continue
            end = pts[-1]
            if prev is not None and math.dist(prev, end) < limit:
                n += 1
            prev = end
    return n


def main():
    paths = sys.argv[1:]
    fonts = [Font(p) for p in paths]
    rows = [report(f) for f in fonts]
    names = [p.split('/')[-2] for p in paths]
    print(f'{"":24}' + ''.join(f'{n:>14}' for n in names))
    for k in rows[0]:
        cells = []
        for r in rows:
            v = r[k]
            if isinstance(v, (int, float)):
                base = rows[0][k]
                pct = f' {100 * (v / base - 1):+.0f}%' if base and abs(v - base) > .5 and k not in ('descender (p)',) else ''
                v = f'{v:.0f}{pct}'
            cells.append(f'{v:>14}')
        print(f'{k:24}' + ''.join(cells))
    ref = contours(fonts[0])
    for n, f in zip(names[1:], fonts[1:]):
        c = contours(f)
        bad = {ch: (ref[ch], c[ch]) for ch in ref if ref[ch] != c[ch]}
        print(f'topology {n}: ' + ('same contours as original' if not bad else f'CHANGED {bad}'))
        steps = {ch: (micro(fonts[0], ch), micro(f, ch)) for ch in dict.fromkeys(KEY)}
        worse = {ch: v for ch, v in steps.items() if v[1] > v[0]}
        print(f'micro-steps {n}: ' + ('none added' if not worse else f'ADDED {worse}'))
    adv = {ch: (fonts[0].width(ch), [f.width(ch) for f in fonts[1:]]) for ch in dict.fromkeys(KEY)}
    same = all(all(w == a for w in ws) for a, ws in adv.values())
    print('advance widths', 'unchanged in every build' if same else adv)


if __name__ == '__main__':
    main()
