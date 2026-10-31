"""Zoomed outline views of one glyph from several builds, side by side,
with on-curve nodes (red) and handles (blue), to inspect joins by eye.

usage: zoom.py OUT.png GLYPH X0 Y0 X1 Y1 FONT.otf [FONT.otf ...]
(X0..Y1: the font-unit window to show; it is scaled to 700 px wide)
"""
import sys

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw


def main():
    out, ch = sys.argv[1], sys.argv[2]
    x0, y0, x1, y1 = (float(v) for v in sys.argv[3:7])
    fonts = sys.argv[7:]
    W = 700
    k = W / (x1 - x0)
    H = int((y1 - y0) * k)
    img = Image.new('RGB', (W * len(fonts) + 20 * (len(fonts) - 1), H), 'white')
    for fi, path in enumerate(fonts):
        tt = TTFont(path)
        gs = tt.getGlyphSet()
        rp = RecordingPen()
        gs[tt.getBestCmap()[ord(ch)]].draw(rp)
        ox = fi * (W + 20)
        panel = Image.new('RGB', (W, H), 'white')   # own canvas, so nothing spills over
        P = lambda p: ((p[0] - x0) * k, (y1 - p[1]) * k)
        polys, cur, nodes, handles = [], [], [], []
        for op, args in rp.value:
            if op == 'moveTo':
                cur = [P(args[0])]; nodes.append(args[0])
            elif op == 'lineTo':
                cur.append(P(args[0])); nodes.append(args[0])
            elif op == 'curveTo':
                p0 = cur[-1]
                a, b, c = (P(q) for q in args)
                for i in range(1, 33):
                    t = i / 32; m = 1 - t
                    cur.append(tuple(m**3 * p0[j] + 3 * m * m * t * a[j] + 3 * m * t * t * b[j] + t**3 * c[j] for j in (0, 1)))
                handles += [(p0, a), (b, c)]
                nodes.append(args[-1])
            elif op in ('closePath', 'endPath'):
                polys.append(cur); cur = []
        mask = Image.new('1', panel.size, 0)
        for poly in polys:
            tmp = Image.new('1', panel.size, 0)
            ImageDraw.Draw(tmp).polygon(poly, fill=1)
            mask = ImageChops.logical_xor(mask, tmp)
        panel.paste((215, 215, 215), mask=mask.convert('L'))
        d = ImageDraw.Draw(panel)
        for poly in polys:
            d.line(poly + [poly[0]], fill=(20, 20, 20), width=2)
        for a, b in handles:
            d.line([a, b], fill=(90, 120, 255), width=1)
            d.ellipse([b[0] - 3, b[1] - 3, b[0] + 3, b[1] + 3], outline=(90, 120, 255))
        for n in nodes:
            x, y = P(n)
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(225, 50, 50))
        img.paste(panel, (ox, 0))
    img.save(out)
    print(out, img.size)


if __name__ == '__main__':
    main()
