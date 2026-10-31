"""AA Bridge Sans Text, step 1: lower contrast and a lighter Regular.

usage (from the repo root):
    python sans-serif/experiments/text/textcut.py [--stem 90] [--ratios 0.75 0.82 0.88] [--power 8]

Writes one static test font per ratio to sans-serif/experiments/text/fonts/,
named "AA Bridge Sans Text C82" and so on, plus the untouched opsz 16 Regular
as "AA Bridge Sans Text Before" for side-by-side proofs. Then run check.py
(stroke checks, --sweep FILE to flag any stroke darker than the stem) and
proof.py (PNG proofs).

How it works. Two opsz 16 instances of the variable font: a light one, chosen
so the n stem comes out at --stem units, and a heavy one, chosen so the top of
o comes out at stem x ratio. Every point starts at the light instance and moves
toward the heavy one across its edge (along the edge's normal), by a share that
depends on how flat the edge is: cos(angle to horizontal) ** power. Crossbars
and curve tops take the heavy weight fully, stems not at all, slopes partly.
Corners sit on two edges and move with each by its own share, so where a stem
meets a crossbar the corner keeps the stem's x and takes the bar's y. The
spines of S s $ § 8 are thick yet nearly flat, so their shares fade out across
the middle of the glyph's height (SPINE, SPINE_BAND).

What did not work, so it is not tried again: (1) x wholly from the light
instance and y wholly from the heavy one darkens every sloping thick stroke
(N, C, G, S spines up to 1.45 x the stem); (2) shares from a per-point stroke
thickness measurement put bumps on 6, 9, G and 8, because neighbouring points
on one curve got different shares.

Advance widths, kerning and the x of mark anchors follow the light instance; y
of mark anchors and of components follows the heavy one. Nothing is redrawn:
widths, terminals, t f r and the figures are untouched and are later steps.

This works on the built variable font, so it is a proofing tool, not the final
method. The final text cut belongs in the source as its own masters.
"""
import argparse
import math
import os
import unicodedata

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.varLib import instancer

HERE = os.path.dirname(os.path.abspath(__file__))
VF = os.path.join(HERE, '..', '..', 'fonts', 'variable', 'AABridgeSans[opsz,wght].ttf')
OPSZ = 16



class Flat(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.segs = []

    def _moveTo(self, p):
        self.cur = self.start = p

    def _lineTo(self, p):
        self.segs.append((self.cur, p))
        self.cur = p

    def _curveToOne(self, a, b, c):
        p0 = self.cur
        for i in range(1, 33):
            t = i / 32
            m = 1 - t
            q = (m**3 * p0[0] + 3 * m * m * t * a[0] + 3 * m * t * t * b[0] + t**3 * c[0],
                 m**3 * p0[1] + 3 * m * m * t * a[1] + 3 * m * t * t * b[1] + t**3 * c[1])
            self.segs.append((self.cur, q))
            self.cur = q

    def _qCurveToOne(self, a, c):
        p0 = self.cur
        for i in range(1, 17):
            t = i / 16
            m = 1 - t
            q = (m * m * p0[0] + 2 * m * t * a[0] + t * t * c[0],
                 m * m * p0[1] + 2 * m * t * a[1] + t * t * c[1])
            self.segs.append((self.cur, q))
            self.cur = q

    def _closePath(self):
        if self.cur != self.start:
            self.segs.append((self.cur, self.start))


def runs(segs, horizontal, v):
    """Ink runs along a scanline: y = v when horizontal, x = v otherwise."""
    hits = []
    for a, b in segs:
        (x0, y0), (x1, y1) = (a, b) if horizontal else ((a[1], a[0]), (b[1], b[0]))
        if (y0 <= v < y1) or (y1 <= v < y0):
            hits.append((x0 + (v - y0) * (x1 - x0) / (y1 - y0), 1 if y1 > y0 else -1))
    hits.sort()
    out, w, st = [], 0, None
    for p, d in hits:
        if w == 0:
            st = p
        w += d
        if w == 0:
            out.append((st, p))
    return out


def measure(font):
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()

    def segs(ch):
        pen = Flat(gs)
        gs[cmap[ord(ch)]].draw(pen)
        return pen.segs

    sx = segs('x')
    xh = max(max(a[1], b[1]) for a, b in sx)
    n = runs(segs('n'), True, xh * 0.35)
    so = segs('o')
    xs = [p[0] for s in so for p in s]
    o = runs(so, False, (min(xs) + max(xs)) / 2)
    sH = segs('H')
    xsH = [p[0] for s in sH for p in s]
    hb = runs(sH, False, (min(xsH) + max(xsH)) / 2)
    return {'stem': n[0][1] - n[0][0], 'o_top': o[-1][1] - o[-1][0],
            'o_bottom': o[0][1] - o[0][0], 'H_bar': hb[0][1] - hb[0][0], 'xh': xh}


def inst(w):
    return instancer.instantiateVariableFont(TTFont(VF), {'wght': w, 'opsz': OPSZ},
                                             updateFontNames=False)


def solve(key, target, lo=100, hi=700):
    """User-space weight at which measure()[key] == target (it rises with weight)."""
    for _ in range(18):
        mid = (lo + hi) / 2
        if measure(inst(mid))[key] < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def take_anchor_y(a, b):
    """Walk two parallel GPOS trees, copying anchor y from b into a."""
    if type(a).__name__ == 'Anchor':
        a.YCoordinate = b.YCoordinate
        if hasattr(a, 'YDeviceTable'):
            a.YDeviceTable = None
        if getattr(a, 'Format', 1) == 3:
            a.Format = 1
        return
    if isinstance(a, list):
        for x, y in zip(a, b):
            take_anchor_y(x, y)
        return
    if hasattr(a, '__dict__'):
        for k, v in vars(a).items():
            if k.startswith('_') or not hasattr(b, k):
                continue
            if isinstance(v, (list,)) or hasattr(v, '__dict__'):
                take_anchor_y(v, getattr(b, k))


def rename(font, family):
    name = font['name']
    ps = family.replace(' ', '') + '-Regular'
    for rec in list(name.names):
        if rec.nameID in (1, 16):
            rec.string = family
        elif rec.nameID in (2, 17):
            rec.string = 'Regular'
        elif rec.nameID == 4:
            rec.string = family + ' Regular'
        elif rec.nameID == 6:
            rec.string = ps
        elif rec.nameID == 3:
            rec.string = ps + ';experiment'


def strokes(font, ch, frac):
    """True thickness of every stroke crossing a horizontal line at frac of the
    glyph's height: for the midpoint of each ink run on that line, the
    shortest run through it over all angles."""
    import math
    gs, cmap = font.getGlyphSet(), font.getBestCmap()
    pen = Flat(gs)
    gs[cmap[ord(ch)]].draw(pen)
    ys = [p[1] for s in pen.segs for p in s]
    y = min(ys) + (max(ys) - min(ys)) * frac
    out = []
    for r0, r1 in runs(pen.segs, True, y):
        cx, cy = (r0 + r1) / 2, y
        best = r1 - r0
        for deg in range(0, 180, 2):
            c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
            segs = [(((p[0] - cx) * c + (p[1] - cy) * s, -(p[0] - cx) * s + (p[1] - cy) * c),
                     ((q[0] - cx) * c + (q[1] - cy) * s, -(q[0] - cx) * s + (q[1] - cy) * c))
                    for p, q in pen.segs]
            for a0, a1 in runs(segs, True, 1e-3):
                if a0 <= 0 <= a1:
                    best = min(best, a1 - a0)
        out.append(best)
    return out


# How fast a sloping edge stops taking the heavy offset: an edge at angle a to
# the horizontal takes cos(a) ** POWER of it. High enough that thick but fairly
# flat spines (S, s) gain little while true crossbars and curve tops gain all.
POWER = 8
CORNER = math.cos(math.radians(15))
# Letters whose thick stroke is a nearly flat spine across the middle. Their
# shares fade out over the middle band of the glyph's height (full at 30% and
# 70%, none at 50%), so the thin tops and bottoms still thicken but the spine
# keeps the light weight. Matched through the glyph's character with
# compatibility decomposition, so accented, superior and suffixed forms follow.
SPINE = set('Ss$§8')
SPINE_BAND = (0.30, 0.70)


def unit(v):
    ln = math.hypot(*v)
    return (v[0] / ln, v[1] / ln) if ln else None


def prep(font):
    """For every outline point of the light instance: the direction(s) it may
    move in and how much of the heavy offset it takes. A smooth point or an
    off-curve point moves across its curve; a corner sits on two edges and
    moves with each by that edge's own share, so where a stem meets a bar, the
    corner keeps the stem's x and takes the bar's y."""
    chars = {}
    for code, gname in font.getBestCmap().items():
        chars.setdefault(gname, chr(code))

    def is_spine(gname):
        ch = chars.get(gname) or chars.get(gname.split('.')[0])
        return bool(ch) and unicodedata.normalize('NFKD', ch)[:1] in SPINE

    glyf = font['glyf']
    out = {}
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.isComposite() or g.numberOfContours <= 0:
            continue
        co, fl = list(g.coordinates), g.flags
        ys = [y for _, y in co]
        y0, y1 = min(ys), max(ys)
        spine = is_spine(name)

        def share(nrm, y):
            s = abs(nrm[1]) ** POWER
            if spine and y1 > y0:
                lo, hi = SPINE_BAND
                t = (y - y0) / (y1 - y0)
                if lo < t < hi:
                    s *= 1 - math.sin(math.pi * (t - lo) / (hi - lo)) ** 2
            return s
        info = []
        start = 0
        for end in g.endPtsOfContours:
            idx = list(range(start, end + 1))
            n = len(idx)
            for j, i in enumerate(idx):
                ip, inx = idx[j - 1], idx[(j + 1) % n]
                p, q, r = co[ip], co[i], co[inx]
                on = fl[i] & 1
                vin, vout = unit((q[0] - p[0], q[1] - p[1])), unit((r[0] - q[0], r[1] - q[1]))
                if on and vin and vout and vin[0] * vout[0] + vin[1] * vout[1] < CORNER:
                    edges = []
                    for v in (vin, vout):
                        nrm = (-v[1], v[0])
                        edges.append((nrm, share(nrm, q[1])))
                    info.append(edges)
                    continue
                if on:
                    tg = unit((r[0] - p[0], r[1] - p[1])) or vin or vout
                else:
                    # an off-curve point: the direction of its curve's middle
                    p0 = p if fl[ip] & 1 else ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
                    p2 = r if fl[inx] & 1 else ((r[0] + q[0]) / 2, (r[1] + q[1]) / 2)
                    tg = unit((p2[0] - p0[0], p2[1] - p0[1]))
                if not tg:
                    info.append([((0.0, 1.0), 0.0)])
                    continue
                nrm = (-tg[1], tg[0])
                info.append([(nrm, share(nrm, q[1]))])
            start = end + 1
        out[name] = info
    return out


def mix(wx, wy, info):
    """Start from the light instance and move each point toward the heavy one
    across its stroke, by its share."""
    a, b = inst(wx), inst(wy)
    ga, gb = a['glyf'], b['glyf']
    for gname in a.getGlyphOrder():
        g, h = ga[gname], gb[gname]
        if g.isComposite():
            for ca, cb in zip(g.components, h.components):
                ca.y = cb.y
            continue
        if gname not in info:
            continue
        ca, cb = list(g.coordinates), list(h.coordinates)
        # the heavy glyph grows on both sides: centre it on the light one
        shift = (min(x for x, _ in ca) + max(x for x, _ in ca)
                 - min(x for x, _ in cb) - max(x for x, _ in cb)) / 2
        new = []
        for pa, pb, edges in zip(ca, cb, info[gname]):
            d = (pb[0] + shift - pa[0], pb[1] - pa[1])
            if len(edges) == 1:
                (n, w), = edges
                s = w * (d[0] * n[0] + d[1] * n[1])
                v = (s * n[0], s * n[1])
            else:
                (n1, w1), (n2, w2) = edges
                b1 = w1 * (d[0] * n1[0] + d[1] * n1[1])
                b2 = w2 * (d[0] * n2[0] + d[1] * n2[1])
                det = n1[0] * n2[1] - n1[1] * n2[0]
                if abs(det) < 0.25:
                    k = max(w1, w2)
                    v = (k * d[0], k * d[1])
                else:
                    v = ((b1 * n2[1] - b2 * n1[1]) / det, (n1[0] * b2 - n2[0] * b1) / det)
            new.append((pa[0] + v[0], pa[1] + v[1]))
        g.coordinates = GlyphCoordinates(new)
        g.coordinates.toInt()
    for gname in a.getGlyphOrder():
        ga[gname].recalcBounds(ga)
    take_anchor_y(a['GPOS'].table, b['GPOS'].table)
    a['head'].modified = a['head'].created
    return a


def solve_mix(wx, target, info):
    """Heavy weight at which the mixed font's o top reaches target."""
    lo, hi = wx, 700
    for _ in range(11):
        mid = (lo + hi) / 2
        if measure(mix(wx, mid, info))['o_top'] < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stem', type=float, default=90)
    ap.add_argument('--ratios', type=float, nargs='+', default=[0.75, 0.82, 0.88])
    ap.add_argument('--power', type=float, default=POWER)
    args = ap.parse_args()
    globals()['POWER'] = args.power
    out = os.path.join(HERE, 'fonts')
    os.makedirs(out, exist_ok=True)
    before = inst(400)
    m0 = measure(before)
    rename(before, 'AA Bridge Sans Text Before')
    before.save(os.path.join(out, 'AABridgeSansTextBefore-Regular.ttf'))
    print(f"before (wght 400): stem {m0['stem']:.0f}  o top {m0['o_top']:.0f}  "
          f"H bar {m0['H_bar']:.0f}  ratio {m0['o_top'] / m0['stem']:.2f}  xh {m0['xh']:.0f}")
    wx = solve('stem', args.stem)
    print(f'light instance: wght {wx:.1f}; power {args.power:g}')
    info = prep(inst(wx))
    for r in args.ratios:
        wy = solve_mix(wx, args.stem * r, info)
        f = mix(wx, wy, info)
        m = measure(f)
        tag = f'C{round(r * 100)}'
        rename(f, f'AA Bridge Sans Text {tag}')
        f.save(os.path.join(out, f'AABridgeSansText{tag}-Regular.ttf'))
        print(f"{tag}: heavy instance wght {wy:.1f}  stem {m['stem']:.0f}  o top {m['o_top']:.0f}  "
              f"o bottom {m['o_bottom']:.0f}  H bar {m['H_bar']:.0f}  "
              f"ratio {m['o_top'] / m['stem']:.2f}  xh {m['xh']:.0f}")


if __name__ == '__main__':
    main()
