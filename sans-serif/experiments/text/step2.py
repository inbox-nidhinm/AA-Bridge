"""AA Bridge Sans Text, step 2: even strokes and plain letters (Regular only).

usage (from the repo root):
    python sans-serif/experiments/text/step2.py [--even 0.96] [--dot 0.79]

Writes fonts/AABridgeSansTextStep2-Regular.ttf ("AA Bridge Sans Text Step2"),
built on the current opsz 16 Regular (stem 104, unchanged). Asked for on
2026-11-01, after step 1:

1. Thin strokes thickened, thick ones left alone, so strokes are nearly the
   same thickness everywhere (--even x the stem), including the thin tops of
   C and G. Each thin stroke grows on its counter side when its other side is
   the letter's silhouette or sits on an alignment line (baseline, x-height,
   cap height), so heights do not change; otherwise it grows on both sides.
   Accents are left alone, and small forms (superiors, fractions) grow only to
   their own stem.
2. Curls and balls removed: a (cut level at the top-left), c (rebuilt from o,
   cut level like C), f (cut upright), g (straight ear in place of the curl),
   6 (cut level), Q (straight diagonal tail).
3. R: straight leg as thick as the stem; its foot ends a little inside the
   bowl's right edge, for optical alignment.
4. S: redrawn from a smooth centre line at an even thickness.
5. E: the middle bar is longer.
6. r: the arm's end is as thick as the stem.
7. Smaller dots on i and j (and every letter with the same dot), with the gap
   above the stem kept.

Accented letters are separate outlines in this font: each one gets the same
change by finding the base letter's contours inside it and swapping them for
the new ones. Superior, inferior and fraction figures are not reshaped.
A proof made on the built font; the final version belongs in the source.
"""
import argparse
import math
import os
import sys
import unicodedata

import pathops
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textcut import Flat, inst, measure, rename, runs, unit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CORNER = math.cos(math.radians(15))

# ---------------------------------------------------------------- outlines


def to_path(glyph, glyf):
    p = pathops.Path()
    glyph.draw(p.getPen(), glyf)
    return p


def rect(x0, y0, x1, y1):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo((x0, y0))
    pen.lineTo((x0, y1))
    pen.lineTo((x1, y1))
    pen.lineTo((x1, y0))
    pen.closePath()
    return p


def poly(pts):
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(pts[0])
    for q in pts[1:]:
        pen.lineTo(q)
    pen.closePath()
    return p


def union(*ps):
    out = ps[0]
    for p in ps[1:]:
        out = pathops.op(out, p, pathops.PathOp.UNION, clockwise=True)
    return pathops.simplify(out, clockwise=True)


def minus(a, b):
    return pathops.op(a, b, pathops.PathOp.DIFFERENCE, clockwise=True)


def intersect(a, b):
    return pathops.op(a, b, pathops.PathOp.INTERSECTION, clockwise=True)


def set_glyph(font, name, path, advance=None):
    pen = TTGlyphPen(None)
    path.draw(Cu2QuPen(pen, max_err=0.5, reverse_direction=False))
    g = pen.glyph()
    font['glyf'][name] = g
    g.recalcBounds(font['glyf'])
    adv = advance if advance is not None else font['hmtx'][name][0]
    font['hmtx'][name] = (int(round(adv)), getattr(g, 'xMin', 0))


def contours(g):
    """A simple glyph's contours as (points, flags) lists."""
    out, start = [], 0
    co = list(g.coordinates)
    for end in g.endPtsOfContours:
        out.append((co[start:end + 1], list(g.flags[start:end + 1])))
        start = end + 1
    return out


def bounds(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def shape_key(pts):
    x0, y0 = pts[0]
    return tuple((round(x - x0), round(y - y0)) for x, y in pts)


def family(font, base):
    """The base glyph and every glyph whose character is that letter plus
    marks (á, ç, ř ...), plus suffixed copies (six.lf), not stylistic sets."""
    rev = {}
    for code, n in font.getBestCmap().items():
        rev.setdefault(n, chr(code))
    bch = rev[base]
    out = []
    for name in font.getGlyphOrder():
        ch = rev.get(name)
        if name == base or (ch and ch != bch and unicodedata.normalize('NFD', ch)[:1] == bch):
            out.append(name)
        elif name.split('.')[0] == base and '.ss' not in name and name != base:
            out.append(name)
    return out


def path_of_contours(cs):
    from fontTools.ttLib.tables._g_l_y_f import Glyph
    g = Glyph()
    g.numberOfContours = len(cs)
    g.coordinates = GlyphCoordinates([p for pts, _ in cs for p in pts])
    g.flags = bytearray(f for _, fl in cs for f in fl)
    ends, n = [], 0
    for pts, _ in cs:
        n += len(pts)
        ends.append(n - 1)
    g.endPtsOfContours = ends
    g.program = None
    p = pathops.Path()
    g.draw(p.getPen(), None)
    return p


# ---------------------------------------------------------------- strokes

def hermite(points, tangents, k=0.40):
    segs = []
    for (p0, t0), (p1, t1) in zip(zip(points, tangents), zip(points[1:], tangents[1:])):
        d = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * k
        segs.append((p0, (p0[0] + t0[0] * d, p0[1] + t0[1] * d),
                     (p1[0] - t1[0] * d, p1[1] - t1[1] * d), p1))
    return segs


def split(seg, t):
    p0, c1, c2, p1 = seg

    def L(a, b):
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    a, b, c = L(p0, c1), L(c1, c2), L(c2, p1)
    d, e = L(a, b), L(b, c)
    m = L(d, e)
    return (p0, a, d, m), (m, e, c, p1)


def offset(seg, h):
    """Tiller-Hanson: offset the control polygon's legs and re-intersect."""
    p0, c1, c2, p1 = seg

    def nrm(a, b):
        u = unit((b[0] - a[0], b[1] - a[1])) or (1.0, 0.0)
        return (-u[1], u[0])

    def shift(a, b):
        n = nrm(a, b)
        return (a[0] + n[0] * h, a[1] + n[1] * h), (b[0] + n[0] * h, b[1] + n[1] * h)

    def meet(l1, l2):
        (x1, y1), (x2, y2) = l1
        (x3, y3), (x4, y4) = l2
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-9:
            return l1[1]
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    a, b, c = shift(p0, c1), shift(c1, c2), shift(c2, p1)
    return a[0], meet(a, b), meet(b, c), c[1]


def stroke(points, tangents, width, k=0.40, sub=4):
    segs = []
    for s in hermite(points, tangents, k):
        rest = s
        for i in range(sub, 1, -1):
            a, rest = split(rest, 1 / i)
            segs.append(a)
        segs.append(rest)
    h = width / 2
    left = [offset(s, h) for s in segs]
    right = [offset((s[3], s[2], s[1], s[0]), h) for s in reversed(segs)]
    p = pathops.Path()
    pen = p.getPen()
    pen.moveTo(left[0][0])
    for s in left:
        pen.curveTo(s[1], s[2], s[3])
    pen.lineTo(right[0][0])
    for s in right:
        pen.curveTo(s[1], s[2], s[3])
    pen.closePath()
    return pathops.simplify(p, clockwise=True)


def bar(a, b, width, end_x=None):
    """A straight stroke from a to b; with end_x, the b end is cut upright there."""
    u = unit((b[0] - a[0], b[1] - a[1]))
    n = (-u[1] * width / 2, u[0] * width / 2)
    pts = [(a[0] + n[0], a[1] + n[1]), (b[0] + n[0], b[1] + n[1]),
           (b[0] - n[0], b[1] - n[1]), (a[0] - n[0], a[1] - n[1])]
    if end_x is not None:
        for i in (1, 2):
            o = pts[i - 1] if i == 1 else pts[3]
            q = pts[i]
            t = (end_x - o[0]) / (q[0] - o[0])
            pts[i] = (end_x, o[1] + t * (q[1] - o[1]))
    return poly(pts)


# ---------------------------------------------------------------- letters

def build_letters(font, stem, even):
    glyf = font['glyf']
    T = stem * even
    path = {n: to_path(glyf[n], glyf) for n in ('o', 'a', 'f', 'g', 'O', 'Q', 'R', 'six', 'S', 'c')}
    xh = measure(font)['xh']
    new = {}

    # c: o cut open on the right, ends cut level like C's
    o = path['o']
    x0, y0, x1, y1 = o.bounds
    cx = (x0 + x1) / 2
    c = minus(o, rect(cx, 0.30 * xh, x1 + 50, 0.70 * xh))
    o_rsb = font['hmtx']['o'][0] - x1
    cb = c.bounds
    new['c'] = (pathops.simplify(c, clockwise=True), cb[2] + 0.75 * o_rsb)

    gs = font.getGlyphSet()

    def ink_runs(name, y):
        pen = Flat(gs)
        gs[name].draw(pen)
        return runs(pen.segs, True, y)

    # a: the top arc redrawn from the stem, at the stem's thickness, without
    # the curl and ball, and cut level at its left end
    a = path['a']
    ax0 = a.bounds[0]
    sl, sr = ink_runs('a', 0.4 * xh)[-1]
    sw, scx = sr - sl, (sl + sr) / 2
    body = minus(a, rect(-100, 0.66 * xh, sr + 100, xh + 200))
    hw = sw / 2
    apex = ((ax0 + sr) / 2 - 8, xh + 12 - hw)
    arc = stroke([(scx, 0.52 * xh), apex, (ax0 + hw + 6, 0.62 * xh)],
                 [(0, 1), (-1, 0), unit((-0.30, -0.95))], sw, k=0.50)
    arc = minus(arc, rect(-100, 0.30 * xh, apex[0] - 40, 0.79 * xh))
    # a straight stem down to the baseline (no nub where the bowl joins it)
    new['a'] = (union(body, arc, rect(sl, 0, sr, 0.55 * xh)), None)

    # f (and fi, fl): the arm redrawn from the stem and cut upright
    def f_arm(name, x_term, keep_from=3000):
        """keep_from: ink right of this x is another letter (fl's l) and stays."""
        p = path.get(name) or to_path(glyf[name], glyf)
        top = max(y for x, y in glyf['f'].coordinates)
        fl_, fr_ = ink_runs(name, 0.3 * xh)[0]
        w, c = fr_ - fl_, (fl_ + fr_) / 2
        body = minus(p, rect(-100, xh + 40, keep_from, 3000))
        P1 = (c + 1.25 * w, top - w / 2)
        P2 = (max(x_term + 60, P1[0] + 120), top - w / 2 - 0.30 * w)
        arm = stroke([(c, xh + 10), P1, P2], [(0, 1), (1, 0), unit((1, -0.25))], w, k=0.50)
        arm = minus(arm, rect(x_term, xh, 3000, 3000))
        return union(body, arm)

    fco = list(glyf['f'].coordinates)
    bar_right = max(x for x, y in fco if 0.85 * xh < y < 1.02 * xh)
    new['f'] = (f_arm('f', bar_right - 15), None)
    i_right = ink_runs('fi', 0.3 * xh)[-1][1]
    new_fi = f_arm('fi', i_right)
    l_left = ink_runs('fl', 0.3 * xh)[-1][0]
    new_fl = f_arm('fl', l_left - 60, keep_from=l_left - 2)
    path['_fi'], path['_fl'] = new_fi, new_fl

    # g: curl and ball of the ear off, a straight ear from the bowl instead
    g = glyf['g']
    keep = [cnt for cnt in contours(g) if not (bounds(cnt[0])[1] > 0.80 * xh and bounds(cnt[0])[0] > 0.60 * xh)]
    gp = path_of_contours(keep)
    bowl = max((cnt for cnt in keep if bounds(cnt[0])[1] > 0), key=lambda c: bounds(c[0])[2] - bounds(c[0])[0])
    bx0, by0, bx1, by1 = bounds(bowl[0])
    gcx, gcy = (bx0 + bx1) / 2, (by0 + by1) / 2
    rx, ry = (bx1 - bx0) / 2 - T / 2, (by1 - by0) / 2 - T / 2
    # a level ear whose top sits on the x-height, leaving the bowl's ring
    # where the ring's centre line is at the ear's centre height
    # The ear's top sits a little under the x-height; it starts at the bowl's
    # centre and is kept out of the counter, so it grows off the bowl's shoulder.
    ey = xh - T / 2 - 25
    counter = min((cnt for cnt in keep if bounds(cnt[0])[0] > bx0 and bounds(cnt[0])[1] > by0
                   and bounds(cnt[0])[2] < bx1), key=lambda c: bounds(c[0])[2] - bounds(c[0])[0])
    ear_x = font['hmtx']['g'][0] - 30
    ear = minus(rect(gcx, ey - T / 2, ear_x, ey + T / 2), path_of_contours([counter]))
    new['g'] = (union(gp, ear), None)

    # 6: ball and curl off, the top arm cut level
    s6 = path['six']
    sx0, sy0, sx1, sy1 = s6.bounds
    w6 = sx1 - sx0
    new['six'] = (minus(s6, rect(sx0 + 0.62 * w6, 0.66 * sy1, sx1 + 50, 0.855 * sy1)), None)

    # Q: O with a straight tail
    O = path['O']
    qx0, qy0, qx1, qy1 = O.bounds
    W, H = qx1 - qx0, qy1 - qy0
    P1 = (qx0 + 0.56 * W, qy0 + 0.20 * H)
    P2 = (qx0 + 0.95 * W, qy0 - 0.17 * H)
    tail = bar(P1, P2, T)
    q = union(O, tail)
    O_rsb = font['hmtx']['O'][0] - qx1
    new['Q'] = (q, max(font['hmtx']['O'][0], q.bounds[2] + 0.6 * O_rsb))

    # R: straight leg, as thick as the stem, foot just inside the bowl's edge
    R = path['R']
    rx0, ry0, rx1, ry1 = R.bounds
    Rg = glyf['R']
    stem_r = min(x for x, y in Rg.coordinates if y > 0.95 * ry1 and x > rx0 + 20)
    bar_bottom = max(y for x, y in Rg.coordinates if 0.35 * ry1 < y < 0.55 * ry1 and abs(x - stem_r) < 3 and y < 0.47 * ry1)
    counter_bottom = min(y for x, y in Rg.coordinates if abs(x - stem_r) < 3 and y > bar_bottom + 5)
    body = minus(R, rect(stem_r + 1, -50, rx1 + 100, bar_bottom))
    # the bar under the bowl at full thickness, growing downward, so the
    # counter keeps its flat bottom
    new_bar_bottom = counter_bottom - T
    top_y = new_bar_bottom + 0.55 * T
    xr = rx1 - 0.014 * (rx1 - rx0) - 2
    xt = stem_r + 0.42 * (rx1 - stem_r)
    wh = stem
    for _ in range(6):
        xb = xr - wh / 2
        th = math.atan2(top_y, xb - xt)
        wh = stem / math.sin(th)
    leg = poly([(xt - wh / 2, top_y), (xt + wh / 2, top_y), (xr, 0), (xr - wh, 0)])
    barr = rect(stem_r - 2, new_bar_bottom, xt + wh / 2, counter_bottom + 1)
    new['R'] = (union(body, barr, leg), None)

    # j: the tail redrawn from the stem as one even stroke, cut upright
    jg = glyf['j']
    jcs = contours(jg)
    stem_tail = [c for c in jcs if bounds(c[0])[1] < 0]
    jp = path_of_contours(stem_tail)
    jx0, jy0, jx1, jy1 = jp.bounds
    jl, jr = ink_runs('j', 0.3 * xh)[0]
    jw, jc = jr - jl, (jl + jr) / 2
    # a quarter turn: down the stem, round to level at the bottom, cut upright
    P1 = (jc - 1.3 * jw, jy0 + jw / 2)
    x_end = P1[0] + 4
    tail = stroke([(jc, 0.25 * xh), P1, (P1[0] - 80, P1[1])],
                  [(0, -1), (-1, 0), (-1, 0)], jw, k=0.55)
    tail = minus(tail, rect(-3000, -3000, x_end, 0))
    jbody = union(rect(jl, 0, jr, max(y for x, y in stem_tail[0][0])), tail)
    new['_j'] = jbody

    # S: a smooth centre line, stroked at an even thickness
    S = path['S']
    L_, B_, R_, Tp = S.bounds
    Hs = Tp - B_
    h = T / 2
    pts = [(R_ - 0.12 * (R_ - L_), B_ + 0.785 * Hs),
           ((L_ + R_) / 2 + 6, Tp - h),
           (L_ + h, B_ + 0.735 * Hs),
           ((L_ + R_) / 2, B_ + 0.508 * Hs),
           (R_ - h, B_ + 0.255 * Hs),
           ((L_ + R_) / 2 - 6, B_ + h),
           (L_ + 0.09 * (R_ - L_), B_ + 0.225 * Hs)]
    tan = [unit((-0.42, 0.91)), (-1, 0), (0, -1), unit((1, -0.40)), (0, -1), (-1, 0), unit((-0.42, 0.91))]
    new['S'] = (stroke(pts, tan, T * 1.02, k=0.42), None)
    return new, path


def apply_family(font, base, new_path, advance, only=None):
    """Swap the base letter's contours (or those passing `only`) for the new
    outline in the base glyph and in every separately drawn accented copy."""
    glyf = font['glyf']
    old = [c for c in contours(glyf[base]) if only is None or only(c[0])]
    keys = {shape_key(p): bounds(p)[:2] for p, _ in old}
    done, skipped = [], []
    old_adv = font['hmtx'][base][0]
    for name in family(font, base):
        g = glyf[name]
        if g.isComposite() or g.numberOfContours <= 0:
            continue
        cs = contours(g)
        hits, rest, offs = [], [], set()
        for pts, fl in cs:
            k = shape_key(pts)
            # the same shape, allowing the 1-2 unit rounding differences the
            # variable font's interpolation leaves between copies
            m = next((kk for kk in keys if len(kk) == len(k) and all(
                abs(a[0] - b[0]) <= 2 and abs(a[1] - b[1]) <= 2 for a, b in zip(k, kk))), None)
            if m is not None:
                bx, by = bounds(pts)[:2]
                ox, oy = keys[m]
                offs.add((round((bx - ox) / 4) * 4, round((by - oy) / 4) * 4))
                hits.append((pts, fl, bx - ox, by - oy))
            else:
                rest.append((pts, fl))
        if hits:
            # the offset of the matched group as a whole (a letter can repeat a
            # contour, like H's two stems, so per-contour offsets can mislead)
            hb = bounds([p for h in hits for p in h[0]])
            ob = bounds([p for c in old for p in c[0]])
            offs = {(round(hb[0] - ob[0]), round(hb[1] - ob[1]))}
        if len(hits) != len(old) or len(offs) != 1:
            skipped.append(name)
            continue
        dx, dy = offs.pop()
        moved = pathops.Path()
        new_path.draw(_Shift(moved.getPen(), dx, dy))
        out = union(moved, path_of_contours(rest)) if rest else moved
        adv = font['hmtx'][name][0]
        if advance is not None:
            adv = adv - old_adv + advance
        set_glyph(font, name, out, adv)
        done.append(name)
    return done, skipped


class _Shift:
    def __init__(self, pen, dx, dy):
        self.pen, self.dx, self.dy = pen, dx, dy

    def _m(self, pts):
        return [(x + self.dx, y + self.dy) for x, y in pts]

    def moveTo(self, p):
        self.pen.moveTo(*self._m([p]))

    def lineTo(self, p):
        self.pen.lineTo(*self._m([p]))

    def curveTo(self, *pts):
        self.pen.curveTo(*self._m(pts))

    def qCurveTo(self, *pts):
        self.pen.qCurveTo(*self._m([p for p in pts if p is not None]))

    def closePath(self):
        self.pen.closePath()

    def endPath(self):
        self.pen.endPath()


def longer_E_bar(font, extra):
    glyf = font['glyf']
    E = glyf['E']
    co = list(E.coordinates)
    ys = [y for _, y in co]
    cap = max(ys)
    mids = [(x, y) for x, y in co if 0.3 * cap < y < 0.7 * cap]
    xmid = max(x for x, _ in mids)
    ylo = min(y for x, y in mids if abs(x - xmid) < 2)
    yhi = max(y for x, y in mids if abs(x - xmid) < 2)
    changed = []
    for name in family(font, 'E'):
        g = glyf[name]
        if g.isComposite():
            continue
        new = [(x + extra, y) if abs(x - xmid) < 2 and ylo - 1 <= y <= yhi + 1 else (x, y)
               for x, y in g.coordinates]
        g.coordinates = GlyphCoordinates(new)
        changed.append(name)
    return changed, (xmid, ylo, yhi)


# ---------------------------------------------------------------- even strokes

def even_strokes(font, stem, even, overrides, skip=()):
    """Bring every thin stroke up to `even` x its glyph's stem."""
    glyf, gs = font['glyf'], font.getGlyphSet()
    m = measure(font)
    zones = [0, m['xh'], 700]
    classes = font['GDEF'].table.GlyphClassDef.classDefs

    def zone(y):
        d = min(abs(y - z) for z in zones)
        return 1.0 if d <= 18 else max(0.0, 1 - (d - 18) / 30)

    report = {}
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.isComposite() or g.numberOfContours <= 0 or classes.get(name) == 3 or name in skip:
            continue
        pen = Flat(gs)
        gs[name].draw(pen)
        segs = pen.segs
        co, fl = list(g.coordinates), g.flags

        def probe(q, n):
            """Thickness across the stroke at outline point q along n, which
            side is the inside, and whether either side looks out into open
            space (the letter's silhouette)."""
            t = (-n[1], n[0])

            def rot(p):
                dx, dy = p[0] - q[0], p[1] - q[1]
                return (dx * n[0] + dy * n[1], dx * t[0] + dy * t[1])
            rs = [(rot(a), rot(b)) for a, b in segs]

            def runs_along(far, v):
                """Is the outline where the ray leaves the stroke roughly
                parallel to the outline at q? True across a stroke; false
                along one (a cut end, a terminal face), where the run length
                is not a thickness."""
                best_d, d = None, None
                for (x0, y0), (x1, y1) in rs:
                    if (y0 <= v < y1) or (y1 <= v < y0):
                        u = x0 + (v - y0) * (x1 - x0) / (y1 - y0)
                        if best_d is None or abs(u - far) < best_d:
                            best_d, d = abs(u - far), unit((x1 - x0, y1 - y0))
                return d is not None and abs(d[1]) > math.cos(math.radians(40))

            best = None
            for v in (0.5, -0.5):
                rr = runs(rs, True, v)
                for i, (a0, a1) in enumerate(rr):
                    if abs(a0) < 4 or abs(a1) < 4:
                        if best is None or a1 - a0 < best[0]:
                            inward = 1 if abs(a0) < 4 else -1
                            far = a1 if inward == 1 else a0
                            if not runs_along(far, v):
                                continue
                            others = rr[:i] + rr[i + 1:]
                            open_self = not any((r1 <= 0.5 if inward == 1 else r0 >= -0.5) for r0, r1 in others)
                            open_far = not any((r0 >= far - 0.5 if inward == 1 else r1 <= far + 0.5) for r0, r1 in others)
                            best = (a1 - a0, inward, far, open_self, open_far)
            return best

        # first pass: thicknesses, to find this glyph's own stem
        pts_info = []
        start = 0
        for end in g.endPtsOfContours:
            idx = list(range(start, end + 1))
            n_ = len(idx)
            for j, i in enumerate(idx):
                ip, inx = idx[j - 1], idx[(j + 1) % n_]
                p, q, r = co[ip], co[i], co[inx]
                vin, vout = unit((q[0] - p[0], q[1] - p[1])), unit((r[0] - q[0], r[1] - q[1]))
                if fl[i] & 1 and vin and vout and vin[0] * vout[0] + vin[1] * vout[1] < CORNER:
                    edges = []
                    for v, other, sgn in ((vin, p, -1), (vout, r, 1)):
                        step = min(8.0, 0.4 * math.hypot(other[0] - q[0], other[1] - q[1]))
                        at = (q[0] + sgn * v[0] * step, q[1] + sgn * v[1] * step)
                        nn = (-v[1], v[0])
                        edges.append((nn, at, probe(at, nn)))
                    pts_info.append(('corner', i, edges))
                    continue
                if fl[i] & 1:
                    at, tg = q, unit((r[0] - p[0], r[1] - p[1])) or vin or vout
                else:
                    p0 = p if fl[ip] & 1 else ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
                    p2 = r if fl[inx] & 1 else ((r[0] + q[0]) / 2, (r[1] + q[1]) / 2)
                    at = ((p0[0] + 2 * q[0] + p2[0]) / 4, (p0[1] + 2 * q[1] + p2[1]) / 4)
                    tg = unit((p2[0] - p0[0], p2[1] - p0[1]))
                if not tg:
                    pts_info.append(('fixed', i, []))
                    continue
                nn = (-tg[1], tg[0])
                pts_info.append(('smooth', i, [(nn, at, probe(at, nn))]))
            start = end + 1
        ts = sorted(e[2][0] for _, _, es in pts_info for e in es if e[2])
        if not ts:
            continue
        own = ts[int(0.8 * (len(ts) - 1))]
        target = min(stem, own) * overrides.get(name, even)

        def move(nn, at, pr):
            if not pr:
                return 0.0, nn
            th, inward, far, open_self, open_far = pr
            if th > 1.6 * stem:
                return 0.0, nn
            D = max(0.0, target - th)
            if D == 0:
                return 0.0, nn
            far_pt = (at[0] + nn[0] * far, at[1] + nn[1] * far)
            flat = abs(nn[1])
            s_self = max(zone(at[1]) * flat, 0.8 if open_self else 0.0)
            s_far = max(zone(far_pt[1]) * flat, 0.8 if open_far else 0.0)
            a, b = 1 - s_self, 1 - s_far
            share = 0.5 if a + b < 1e-6 else a / (a + b)
            out = (-nn[0] * inward, -nn[1] * inward)        # away from the stroke
            return share * D, out

        disp = [(0.0, 0.0)] * len(co)
        kinds = {}
        for kind, i, edges in pts_info:
            kinds[i] = kind
            if kind == 'fixed':
                continue
            if kind == 'smooth':
                d, out = move(*edges[0])
                disp[i] = (out[0] * d, out[1] * d)
            else:
                (n1, a1, p1), (n2, a2, p2) = edges
                d1, o1 = move(n1, a1, p1)
                d2, o2 = move(n2, a2, p2)
                det = o1[0] * o2[1] - o1[1] * o2[0]
                if abs(det) < 0.25:
                    k = max(d1, d2)
                    o = unit((o1[0] + o2[0], o1[1] + o2[1])) or o1
                    disp[i] = (o[0] * k, o[1] * k)
                else:
                    v = ((d1 * o2[1] - d2 * o1[1]) / det, (o1[0] * d2 - o2[0] * d1) / det)
                    cap = 1.3 * max(d1, d2)
                    ln = math.hypot(*v)
                    disp[i] = v if ln <= cap or ln == 0 else (v[0] * cap / ln, v[1] * cap / ln)
        # straight level edges stay level and straight upright edges stay
        # upright: both ends take the larger of their two moves
        start = 0
        for end in g.endPtsOfContours:
            idx = list(range(start, end + 1))
            n_ = len(idx)
            for j in range(n_):
                i, k = idx[j], idx[(j + 1) % n_]
                if not (fl[i] & 1 and fl[k] & 1):
                    continue
                (x1, y1), (x2, y2) = co[i], co[k]
                if abs(y1 - y2) < 1 and abs(x1 - x2) > 10:
                    dy = max(disp[i][1], disp[k][1], key=abs)
                    disp[i], disp[k] = (disp[i][0], dy), (disp[k][0], dy)
                elif abs(x1 - x2) < 1 and abs(y1 - y2) > 10:
                    dx = max(disp[i][0], disp[k][0], key=abs)
                    disp[i], disp[k] = (dx, disp[i][1]), (dx, disp[k][1])
            start = end + 1
        # smooth along each contour, corners held
        for _ in range(2):
            new = list(disp)
            start = 0
            for end in g.endPtsOfContours:
                idx = list(range(start, end + 1))
                n_ = len(idx)
                for j, i in enumerate(idx):
                    if kinds.get(i) != 'smooth':
                        continue
                    a, b = disp[idx[j - 1]], disp[idx[(j + 1) % n_]]
                    new[i] = (0.25 * a[0] + 0.5 * disp[i][0] + 0.25 * b[0],
                              0.25 * a[1] + 0.5 * disp[i][1] + 0.25 * b[1])
                start = end + 1
            disp = new
        g.coordinates = GlyphCoordinates([(x + d[0], y + d[1]) for (x, y), d in zip(co, disp)])
        g.coordinates.toInt()
        g.recalcBounds(glyf)
        report[name] = round(own)
    return report


# ---------------------------------------------------------------- dots

def smaller_dots(font, factor):
    glyf = font['glyf']
    i = glyf['i']
    cs = contours(i)
    dot = max(cs, key=lambda c: bounds(c[0])[1])
    key = shape_key(dot[0])
    dx0, dy0, dx1, dy1 = bounds(dot[0])
    xh = measure(font)['xh']
    changed = []
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.isComposite() or g.numberOfContours <= 0:
            continue
        cs = contours(g)
        hit = False
        out = []
        for pts, fl in cs:
            k = shape_key(pts)
            b = bounds(pts)
            same_size = abs((b[2] - b[0]) - (dx1 - dx0)) <= 3 and abs((b[3] - b[1]) - (dy1 - dy0)) <= 3
            if same_size and b[1] > xh + 30 and len(k) == len(key) and all(
                    abs(a[0] - c[0]) <= 2 and abs(a[1] - c[1]) <= 2 for a, c in zip(k, key)):
                x0, y0, x1, y1 = bounds(pts)
                ax, ay = (x0 + x1) / 2, y0
                pts = [(ax + (x - ax) * factor, ay + (y - ay) * factor) for x, y in pts]
                hit = True
            out.append((pts, fl))
        if hit:
            g.coordinates = GlyphCoordinates([p for pts, _ in out for p in pts])
            g.coordinates.toInt()
            g.recalcBounds(glyf)
            changed.append(name)
    return changed


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--even', type=float, default=0.96)
    ap.add_argument('--dot', type=float, default=0.79)
    ap.add_argument('--e-bar', type=float, default=70)
    args = ap.parse_args()

    font = inst(400)
    stem = measure(font)['stem']
    print(f'stem {stem:.0f}, strokes brought up to {args.even:.2f} x stem ({stem * args.even:.0f})')
    # dots first, while every dot is still the same outline as i's
    dots = smaller_dots(font, args.dot)
    print(f'smaller dots ({len(dots)}): {" ".join(dots)}')

    new, paths = build_letters(font, stem, args.even)
    jbody = new.pop('_j')
    done, skipped = apply_family(font, 'j', jbody, None, only=lambda pts: bounds(pts)[1] < 0)
    print(f'j: {len(done)} glyphs' + (f'; not matched: {" ".join(skipped)}' if skipped else ''))
    for base, (path, adv) in new.items():
        done, skipped = apply_family(font, base, path, adv)
        print(f'{base}: {len(done)} glyphs' + (f'; not matched: {" ".join(skipped)}' if skipped else ''))
    set_glyph(font, 'fi', paths['_fi'])
    set_glyph(font, 'fl', paths['_fl'])
    print('fi, fl: arm redrawn')
    changed, (x, y0, y1) = longer_E_bar(font, args.e_bar)
    print(f'E bar end {x:.0f} -> {x + args.e_bar:.0f} in {len(changed)} glyphs')

    # merge overlapping pieces (crossbars laid over stems, arches over stems)
    # into one outline per glyph, so every edge can be measured and moved
    merged = 0
    for name in font.getGlyphOrder():
        g = font['glyf'][name]
        if g.isComposite() or g.numberOfContours <= 1:
            continue
        set_glyph(font, name, pathops.simplify(to_path(g, font['glyf']), clockwise=True))
        merged += 1
    print(f'overlaps merged in {merged} glyphs')
    rep = even_strokes(font, stem, args.even, {n: 1.0 for n in family(font, 'r')})
    print(f'even strokes: {len(rep)} glyphs')

    glyf, hmtx = font['glyf'], font['hmtx']
    for name in font.getGlyphOrder():
        glyf[name].recalcBounds(glyf)
        adv = hmtx[name][0]
        hmtx[name] = (adv, getattr(glyf[name], 'xMin', 0))
    rename(font, 'AA Bridge Sans Text Step2')
    out = os.path.join(HERE, 'fonts', 'AABridgeSansTextStep2-Regular.ttf')
    font.save(out)
    print('wrote', os.path.relpath(out))


if __name__ == '__main__':
    main()
