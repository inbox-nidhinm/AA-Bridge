"""SVG boards for the tall experiment (glyphs as vectors, no live text, so
they can go onto the Figma Type page; labels are added there in Inter).

usage: board.py ORIGINAL.otf TALL.otf OUTDIR [PLAIN.otf BANDS.otf]

  line.svg     the sample line, original above tall, shaped with HarfBuzz
               (kerning on), with each font's guides
  ghost.svg    every key letter tall in ink with the original outlined in red
               on top, same baseline and origin (advance widths are equal)
  methods.svg  H S e a by the three ways of getting taller: plain stretch,
               bands (heighten.py), compensated; original first
"""
import os
import sys

import pathops
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

INK, GHOST, GUIDE, BASE = '#111111', '#E5484D', '#E2E2E2', '#9EC5FF'
KEY = 'HORSAandglovesxpy'
LINE = 'Handgloves HORSA xpy'


class Font:
    def __init__(self, path):
        self.path = path
        self.tt = TTFont(path)
        self.gs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.order = self.tt.getGlyphOrder()
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(path)))

    def name(self, ch):
        return self.cmap[ord(ch)]

    def d(self, name, s, ox, oy, merge=False):
        pen = SVGPathPen(self.gs, ntos=lambda v: f'{round(v, 2):g}')
        tp = TransformPen(pen, (s, 0, 0, -s, ox, oy))
        if merge:   # silhouette only, for outlines
            p = pathops.Path()
            self.gs[name].draw(p.getPen(glyphSet=self.gs))
            p.simplify()
            p.draw(tp)
        else:
            self.gs[name].draw(tp)
        return pen.getCommands()

    def metric(self, ch, top=True):
        from fontTools.pens.boundsPen import BoundsPen
        b = BoundsPen(self.gs)
        self.gs[self.name(ch)].draw(b)
        return b.bounds[3] if top else b.bounds[1]

    def guides(self):
        return {'asc': self.metric('d'), 'cap': self.metric('H'), 'x': self.metric('x'),
                'base': 0, 'desc': self.metric('p', top=False)}

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {'kern': True, 'liga': True})
        return [(self.order[i.codepoint], p.x_advance, p.x_offset) for i, p in zip(buf.glyph_infos, buf.glyph_positions)]


def guide_lines(f, s, x0, x1, base):
    out = []
    for k, y in f.guides().items():
        col = BASE if k == 'base' else GUIDE
        out.append(f'<path data-guide="{k}" stroke="{col}" stroke-width="1" fill="none" d="M{x0:.1f} {base - y * s:.2f}H{x1:.1f}"/>')
    return out


def svg(path, w, h, body):
    with open(path, 'w') as fh:
        fh.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{round(w)}" height="{round(h)}" viewBox="0 0 {w:.2f} {h:.2f}">\n')
        fh.write('\n'.join(body))
        fh.write('\n</svg>\n')
    print(path, round(w), 'x', round(h))


def line_board(orig, tall, out, size=96, pad=48):
    s = size / 1000
    top, bottom = max(tall.guides()['asc'], 900), min(tall.guides()['desc'], -250)
    row = (top - bottom) * s + 32
    body, width = [], 0
    rows = []
    for i, f in enumerate((orig, tall)):
        base = pad + top * s + i * row
        x = pad
        glyphs = []
        for name, adv, off in f.shape(LINE):
            d = f.d(name, s, x + off * s, base)
            if d:
                glyphs.append(f'<path data-glyph="{name}" fill="{INK}" d="{d}"/>')
            x += adv * s
        width = max(width, x + pad)
        rows.append((f, base, glyphs))
    for f, base, glyphs in rows:
        body += guide_lines(f, s, 0, width, base)
        body.append('<g>' + ''.join(glyphs) + '</g>')
    svg(out, width, pad * 2 + top * s - bottom * s + row, body)


def ghost_board(orig, tall, out, size=160, cols=9, pad=32):
    s = size / 1000
    top, bottom = 900, -260
    cw = max(tall.gs[tall.name(c)].width for c in KEY) * s + 24
    ch_ = (top - bottom) * s
    keys = list(dict.fromkeys(KEY))
    rows = (len(keys) + cols - 1) // cols
    W, H = cols * cw + 2 * pad, rows * ch_ + 2 * pad
    body = []
    for r in range(rows):
        base = pad + top * s + r * ch_
        body += guide_lines(tall, s, pad, W - pad, base)
    for i, c in enumerate(keys):
        col, r = i % cols, i // cols
        base = pad + top * s + r * ch_
        adv = tall.gs[tall.name(c)].width * s
        ox = pad + col * cw + (cw - adv) / 2
        body.append(f'<path data-glyph="{c}" fill="{INK}" d="{tall.d(tall.name(c), s, ox, base)}"/>')
        body.append(f'<path data-glyph="{c}-original" fill="none" stroke="{GHOST}" stroke-width="1.25" '
                    f'd="{orig.d(orig.name(c), s, ox, base, merge=True)}"/>')
    svg(out, W, H, body)


def methods_board(fonts, out, letters='HSea', size=200, pad=32, gap=40):
    s = size / 1000
    top, bottom = 900, -60
    col_w = sum(fonts[0].gs[fonts[0].name(c)].width for c in letters) * s + gap
    H = (top - bottom) * s + 2 * pad
    W = len(fonts) * col_w - gap + 2 * pad
    body = []
    for fi, f in enumerate(fonts):
        x = pad + fi * col_w
        base = pad + top * s
        body += guide_lines(f, s, x, x + col_w - gap, base)
        for c in letters:
            body.append(f'<path data-glyph="{c}" fill="{INK}" d="{f.d(f.name(c), s, x, base)}"/>')
            x += f.gs[f.name(c)].width * s
    svg(out, W, H, body)


def main():
    orig, tall, outdir = Font(sys.argv[1]), Font(sys.argv[2]), sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    line_board(orig, tall, os.path.join(outdir, 'line.svg'))
    ghost_board(orig, tall, os.path.join(outdir, 'ghost.svg'))
    if len(sys.argv) > 5:
        plain, bands = Font(sys.argv[4]), Font(sys.argv[5])
        methods_board([orig, plain, bands, tall], os.path.join(outdir, 'methods.svg'))


if __name__ == '__main__':
    main()
