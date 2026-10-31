"""Glyph outlines on a 50-unit grid, for planning edits.

usage (from the repo root):
    python sans-serif/experiments/text/plot.py FONT.ttf OUT.png glyphname [glyphname ...]
"""
import sys

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

S = 0.5           # pixels per font unit
TOP, BOT = 800, -250


class Poly(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.polys, self.on, self.off = [], [], []

    def _moveTo(self, p):
        self.polys.append([p])
        self.on.append(p)

    def _lineTo(self, p):
        self.polys[-1].append(p)
        self.on.append(p)

    def _curveToOne(self, a, b, c):
        p0 = self.polys[-1][-1]
        for i in range(1, 17):
            t = i / 16
            m = 1 - t
            self.polys[-1].append((m**3 * p0[0] + 3 * m * m * t * a[0] + 3 * m * t * t * b[0] + t**3 * c[0],
                                   m**3 * p0[1] + 3 * m * m * t * a[1] + 3 * m * t * t * b[1] + t**3 * c[1]))
        self.off += [a, b]
        self.on.append(c)

    def _qCurveToOne(self, a, c):
        p0 = self.polys[-1][-1]
        for i in range(1, 13):
            t = i / 12
            m = 1 - t
            self.polys[-1].append((m * m * p0[0] + 2 * m * t * a[0] + t * t * c[0],
                                   m * m * p0[1] + 2 * m * t * a[1] + t * t * c[1]))
        self.off.append(a)
        self.on.append(c)

    def _closePath(self):
        pass


font = TTFont(sys.argv[1])
gs = font.getGlyphSet()
names = sys.argv[3:]
lab = ImageFont.truetype('/System/Library/Fonts/SFNSMono.ttf', 11)
big = ImageFont.truetype('/System/Library/Fonts/SFNSMono.ttf', 16)
panels = []
for name in names:
    w = gs[name].width
    W, H = int((w + 100) * S), int((TOP - BOT) * S)
    im = Image.new('RGB', (W, H + 24), 'white')
    d = ImageDraw.Draw(im)

    def P(x, y):
        return ((x + 50) * S, (TOP - y) * S + 24)
    for gx in range(-50, w + 51, 50):
        d.line([P(gx, BOT), P(gx, TOP)], fill=(235, 235, 235) if gx % 100 else (205, 205, 205))
        if gx % 100 == 0:
            d.text((P(gx, BOT)[0] + 2, H + 24 - 13), str(gx), font=lab, fill=(120, 120, 120))
    for gy in range(-250, 801, 50):
        d.line([P(-50, gy), P(w + 50, gy)], fill=(235, 235, 235) if gy % 100 else (205, 205, 205))
        if gy % 100 == 0:
            d.text((2, P(0, gy)[1] - 12), str(gy), font=lab, fill=(120, 120, 120))
    d.line([P(0, BOT), P(0, TOP)], fill=(255, 150, 150))
    d.line([P(w, BOT), P(w, TOP)], fill=(255, 150, 150))
    pen = Poly(gs)
    gs[name].draw(pen)
    mask = Image.new('L', im.size, 0)
    md = ImageDraw.Draw(mask)
    for poly in pen.polys:
        md.polygon([P(*p) for p in poly], fill=255, outline=255)
    # even-odd fill so counters show
    acc = Image.new('L', im.size, 0)
    for poly in pen.polys:
        m = Image.new('L', im.size, 0)
        ImageDraw.Draw(m).polygon([P(*p) for p in poly], fill=255)
        acc = Image.eval(Image.merge('RGB', (acc, m, m)).convert('L'), lambda v: v) if False else \
            Image.composite(Image.eval(acc, lambda v: 255 - v), acc, m)
    im.paste((150, 160, 185), mask=acc.point(lambda v: 110 if v else 0))
    for poly in pen.polys:
        d.line([P(*p) for p in poly] + [P(*poly[0])], fill=(30, 40, 90), width=1)
    for p in pen.on:
        x, y = P(*p)
        d.rectangle([x - 2, y - 2, x + 2, y + 2], fill=(200, 40, 40))
    for p in pen.off:
        x, y = P(*p)
        d.ellipse([x - 2, y - 2, x + 2, y + 2], outline=(40, 120, 200))
    d.text((6, 4), f'{name}  adv {w}', font=big, fill=(0, 0, 0))
    panels.append(im)
W = sum(p.width for p in panels) + 10 * len(panels)
out = Image.new('RGB', (W, max(p.height for p in panels)), 'white')
x = 0
for p in panels:
    out.paste(p, (x, 0))
    x += p.width + 10
out.save(sys.argv[2])
