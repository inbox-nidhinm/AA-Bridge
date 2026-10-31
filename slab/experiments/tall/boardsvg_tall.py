"""SVGs for the Figma type board of AA Bridge Slab Tall: a sample line and the
full glyph grid, drawn from a static font's outlines.

usage: boardsvg_tall.py FONT.otf LINE.svg GRID.svg [--baseline PX]

The layout of Montagu Slab/tools/boardsvg.py (the AA Bridge Slab board):
line "Hamburgefonstiv Quick Jazz agog Qg" at 96 px, kerned, 48 px either
side, baseline 144 px down a 220.8 px strip; grid of every inked glyph at
64 px in 32 columns of 86.4 x 102.4 px cells, each glyph centred on its
advance. The one change: the grid cells are 10% taller (112.64 px, baseline
88 px down, instead of 102.4 and 69.6) so the taller accented capitals and
the deeper descenders stay inside their cells.
"""
import argparse

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

INK = '#111111'
TEXT = 'Hamburgefonstiv Quick Jazz agog Qg'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('font')
    ap.add_argument('line')
    ap.add_argument('grid')
    ap.add_argument('--baseline', type=float, default=88.0)
    ap.add_argument('--cell', type=float, default=112.64)
    a = ap.parse_args()

    tt = TTFont(a.font)
    gs = tt.getGlyphSet()
    upm = tt['head'].unitsPerEm
    order = tt.getGlyphOrder()

    def fmt(v, nd):
        return f'{round(v, nd):g}'

    def path(name, s, ox, oy, nd):
        pen = SVGPathPen(gs, ntos=lambda v: fmt(v, nd))
        gs[name].draw(TransformPen(pen, (s, 0, 0, -s, ox, oy)))
        return pen.getCommands()

    def bounds(name):
        b = BoundsPen(gs)
        gs[name].draw(b)
        return b.bounds

    # sample line
    s = 96 / upm
    font = hb.Font(hb.Face(hb.Blob.from_file_path(a.font)))
    buf = hb.Buffer()
    buf.add_str(TEXT)
    buf.guess_segment_properties()
    hb.shape(font, buf, {'kern': True, 'liga': True})
    x = 48.0
    parts = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        if bounds(name):
            parts.append(f'<path data-glyph="{name}" fill="{INK}" d="{path(name, s, x + pos.x_offset * s, 144, 3)}"/>')
        x += pos.x_advance * s
    w = x + 48
    with open(a.line, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{round(w)}" height="221" viewBox="0 0 {w:.2f} 220.80">\n'
                f'<g id="glyphs">{"".join(parts)}</g>\n</svg>\n')

    # glyph grid
    s = 64 / upm
    CW, CH, COLS = 86.4, a.cell, 32
    names = [n for n in order if n != '.notdef' and bounds(n)]
    top = max(bounds(n)[3] for n in names) * s
    bottom = -min(bounds(n)[1] for n in names) * s
    rows = (len(names) + COLS - 1) // COLS
    W, H = CW * COLS, CH * rows
    cells = ' '.join([f'M{c * CW:.2f} 0V{H:.2f}' for c in range(COLS + 1)] + [f'M0 {r * CH:.2f}H{W:.2f}' for r in range(rows + 1)])
    parts = []
    for i, n in enumerate(names):
        col, row = i % COLS, i // COLS
        adv = tt['hmtx'][n][0] * s
        parts.append(f'<path data-glyph="{n}" fill="{INK}" d="{path(n, s, col * CW + (CW - adv) / 2, row * CH + a.baseline, 1)}"/>')
    with open(a.grid, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{round(W)}" height="{round(H)}" viewBox="0 0 {W:.2f} {H:.2f}">\n'
                f'<path id="cells" fill="none" stroke="#E2E2E2" stroke-width="1" d="{cells}"/>\n'
                f'<g id="glyphs">\n' + '\n'.join(parts) + '\n</g>\n</svg>\n')
    print(a.font.split('/')[-1], 'line', round(w), 'grid glyphs', len(names), 'rows', rows,
          f'ink {top:.1f}px above / {bottom:.1f}px below baseline; room {a.baseline:.1f} / {CH - a.baseline:.1f}')


if __name__ == '__main__':
    main()
