"""Check AA Bridge Slab Tall against AA Bridge Slab, every weight and size.

usage: check_family.py ORIGINAL-VF.ttf TALL-VF.ttf

At wght 100..700 (user values) x opsz 16 and 144, for every glyph: same
contour count after overlaps are merged (topology), no added micro-steps,
same advance width; and per location the stroke measurements of check.py
side by side (stems, hairlines, serifs, H bar, diagonals, spines) plus the
vertical metrics.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pathops  # noqa: E402

import check  # noqa: E402

WEIGHTS = (100, 200, 300, 400, 500, 600, 700)
SIZES = (144, 16)
STROKES = ('stem n', 'stem H', 'o side (thick)', 'o top / bottom (thin)', 'O top / bottom (thin)', 'H bar',
           'n foot serif', 'v thick diagonal', 'A thick diagonal', 'x thick diagonal', 'S spine', 's spine')
METRICS = ('x-height', 'cap height', 'ascender (d)', 'descender (p)', 'overshoot o / O')


class VFont(check.Font):
    def __init__(self, path, loc):
        super().__init__(path)
        self.gs = self.tt.getGlyphSet(location=loc)


def merged(f, name):
    p = pathops.Path()
    f.gs[name].draw(p.getPen(glyphSet=f.gs))
    p.simplify()
    return p


def micro_count(p, limit=2.0):
    import math
    n = 0
    for c in p.contours:
        prev = None
        for op, pts in c.segments:
            if op == 'moveTo':
                prev = pts[0]
                continue
            if op == 'closePath' or not pts:
                continue
            if prev is not None and math.dist(prev, pts[-1]) < limit:
                n += 1
            prev = pts[-1]
    return n


def fmt(v):
    return f'{v:.0f}' if isinstance(v, (int, float)) else str(v)


def main():
    orig_path, tall_path = sys.argv[1:3]
    problems = []
    for o in SIZES:
        print(f'\n=== opsz {o}')
        print(f'{"":24}' + ''.join(f'{w:>13}' for w in WEIGHTS))
        rows = {}
        for w in WEIGHTS:
            loc = {'wght': w, 'opsz': o}
            fo, ft = VFont(orig_path, loc), VFont(tall_path, loc)
            ro, rt = check.report(fo), check.report(ft)
            for k in METRICS + STROKES:
                rows.setdefault(k, []).append(f'{fmt(ro[k])}>{fmt(rt[k])}')
            names = [n for n in fo.tt.getGlyphOrder() if n in ft.gs]
            for n in names:
                po, pt = merged(fo, n), merged(ft, n)
                co, ct = len(list(po.contours)), len(list(pt.contours))
                if co != ct:
                    problems.append(f'topology {n} @{w},{o}: {co} -> {ct}')
                mo, mt = micro_count(po), micro_count(pt)
                if mt > mo:
                    problems.append(f'micro-step {n} @{w},{o}: {mo} -> {mt}')
                if fo.gs[n].width != ft.gs[n].width:
                    problems.append(f'width {n} @{w},{o}: {fo.gs[n].width} -> {ft.gs[n].width}')
        for k, cells in rows.items():
            print(f'{k:24}' + ''.join(f'{c:>13}' for c in cells))
    print(f'\nglyph checks at {len(WEIGHTS) * len(SIZES)} locations: ' + ('all pass' if not problems else f'{len(problems)} problems'))
    summary = {}
    for p in problems:
        kind, rest = p.split(' ', 1)
        where = rest.split('@')[1].split(':')[0]
        summary[(kind, where)] = summary.get((kind, where), 0) + 1
    for (kind, where), n in sorted(summary.items()):
        print(f'  {kind:11} @{where:8} {n}')
    for p in problems:
        print('  ' + p)


if __name__ == '__main__':
    main()
