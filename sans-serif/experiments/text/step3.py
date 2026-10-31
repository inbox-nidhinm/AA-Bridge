"""AA Bridge Sans Text, step 3: every letter redrawn at one stroke width.

usage (from the repo root):
    python sans-serif/experiments/text/step3.py [--weight 100]

Writes fonts/AABridgeSansTextStep3-Regular.ttf ("AA Bridge Sans Text Step3").
Asked for on 2026-11-01, after step 2: strokes the same width in every letter,
varying only (and only a little) where strokes join; t without its curved
foot; no circles on a, c, f; the single-storey g as the default.

Every basic letter and figure (a-z, A-Z, 0-9, fi, fl) is drawn from centre
lines with one pen of --weight units: rings for o and the bowls, arches for
n m h, straight strokes for stems, bars and diagonals, smooth strokes for S s
2 3 5 6 9 J j g. Ends are cut level at the baseline, x-height and cap height,
or square across the stroke. Where strokes join they simply overlap, so a
joint is at most slightly heavier, never thinner.

Each letter keeps its current advance width, height and stem positions (read
from the current font), so spacing, kerning and accents still fit; t and f
are narrower now that their curls are gone. Accented letters get the new base
letter with their accents kept. Glyphs not redrawn here (punctuation, symbols,
ß æ œ and other extras) go through step 2's even-stroke pass.
A proof built on the current Regular; the final version belongs in the source.
"""
import argparse
import math
import os
import sys

import pathops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textcut import Flat, inst, measure, rename, runs, unit  # noqa: E402
from step2 import (apply_family, bounds, contours, even_strokes, family, minus,  # noqa: E402
                   offset, path_of_contours, poly, rect, set_glyph, smaller_dots,
                   split, to_path, union)

HERE = os.path.dirname(os.path.abspath(__file__))
K = 0.58            # curve fullness: 0.552 is a circle, higher is squarer

# ---------------------------------------------------------------- centre lines


def L(p0, p1):
    return (p0, (p0[0] + (p1[0] - p0[0]) / 3, p0[1] + (p1[1] - p0[1]) / 3),
            (p0[0] + 2 * (p1[0] - p0[0]) / 3, p0[1] + 2 * (p1[1] - p0[1]) / 3), p1)


def Q(cx, cy, rx, ry, a, ccw=True, k=K):
    """A quarter of an ellipse from angle a (0 = right, 90 = top), turning
    anticlockwise (ccw) or clockwise."""
    t0 = math.radians(a)
    t1 = t0 + (math.pi / 2 if ccw else -math.pi / 2)
    s = 1 if ccw else -1

    def P(t):
        return (cx + rx * math.cos(t), cy + ry * math.sin(t))

    def D(t):
        return (-rx * math.sin(t), ry * math.cos(t))
    p0, p1 = P(t0), P(t1)
    d0, d1 = D(t0), D(t1)
    return (p0, (p0[0] + s * k * d0[0], p0[1] + s * k * d0[1]),
            (p1[0] - s * k * d1[0], p1[1] - s * k * d1[1]), p1)


def H(p0, t0, p1, t1, k=0.42):
    """A free curve from p0 leaving along t0 to p1 arriving along t1."""
    d = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * k
    t0, t1 = unit(t0), unit(t1)
    return (p0, (p0[0] + t0[0] * d, p0[1] + t0[1] * d), (p1[0] - t1[0] * d, p1[1] - t1[1] * d), p1)


def _subdivide(segs, n=4):
    out = []
    for s in segs:
        rest = s
        for i in range(n, 1, -1):
            a, rest = split(rest, 1 / i)
            out.append(a)
        out.append(rest)
    return out


def _draw(pen, side):
    pen.moveTo(side[0][0])
    for s in side:
        pen.curveTo(s[1], s[2], s[3])


def pen_stroke(segs, closed=False):
    """Outline a centre line (cubic segments) with the pen: square ends, or a
    ring when closed."""
    segs = _subdivide(segs)
    left = [offset(s, HW) for s in segs]
    right = [offset((s[3], s[2], s[1], s[0]), HW) for s in reversed(segs)]
    if closed:
        a, b = pathops.Path(), pathops.Path()
        pa, pb = a.getPen(), b.getPen()
        _draw(pa, left)
        pa.closePath()
        _draw(pb, right)
        pb.closePath()
        return pathops.op(pathops.simplify(a), pathops.simplify(b), pathops.PathOp.XOR, clockwise=True)
    p = pathops.Path()
    pen = p.getPen()
    _draw(pen, left)
    pen.lineTo(right[0][0])
    for s in right:
        pen.curveTo(s[1], s[2], s[3])
    pen.closePath()
    return pathops.simplify(p, clockwise=True)


def ring(x0, y0, x1, y1, k=K):
    """A round bowl whose outside fills the box."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 - HW, (y1 - y0) / 2 - HW
    return pen_stroke([Q(cx, cy, rx, ry, a, True, k) for a in (0, 90, 180, 270)], closed=True)


def dot(cx, y0, d):
    r = d / 2
    k = 0.552 * r
    p = pathops.Path()
    pen = p.getPen()
    cy = y0 + r
    pen.moveTo((cx + r, cy))
    pen.curveTo((cx + r, cy + k), (cx + k, cy + r), (cx, cy + r))
    pen.curveTo((cx - k, cy + r), (cx - r, cy + k), (cx - r, cy))
    pen.curveTo((cx - r, cy - k), (cx - k, cy - r), (cx, cy - r))
    pen.curveTo((cx + k, cy - r), (cx + r, cy - k), (cx + r, cy))
    pen.closePath()
    return pathops.simplify(p, clockwise=True)


def stem(xc, y0, y1):
    return rect(xc - HW, y0, xc + HW, y1)


def hbar(x0, x1, yc):
    return rect(x0, yc - HW, x1, yc + HW)


def band(path, y0, y1):
    return pathops.op(path, rect(-3000, y0, 3000, y1), pathops.PathOp.INTERSECTION, clockwise=True)


def edge_stroke(e0, e1, side, y0, y1):
    """A straight stroke whose one edge runs through e0 and e1 (extended), the
    pen's width to the given side (+1 right of e0->e1, -1 left), cut level at
    y0 and y1."""
    u = unit((e1[0] - e0[0], e1[1] - e0[1]))
    n = (u[1] * side, -u[0] * side)
    a = (e0[0] - u[0] * 2000, e0[1] - u[1] * 2000)
    b = (e1[0] + u[0] * 2000, e1[1] + u[1] * 2000)
    return band(poly([a, b, (b[0] + n[0] * PEN, b[1] + n[1] * PEN), (a[0] + n[0] * PEN, a[1] + n[1] * PEN)]), y0, y1)


def inset(x_outer, sgn, y_a, y_b, x_far):
    """Centre-line x at height y_a for a straight stroke whose outer edge is at
    x_outer there and whose centre line reaches x_far at y_b; sgn +1 insets to
    the right, -1 to the left. The stroke's horizontal width depends on its
    slope, so this settles it by repeating."""
    wh = PEN
    xc = x_outer
    for _ in range(10):
        xc = x_outer + sgn * wh / 2
        th = math.atan2(abs(y_a - y_b), abs(x_far - xc))
        wh = PEN / max(0.2, math.sin(th))
    return xc, wh


def segment(p0, p1, y0, y1):
    """A finite straight stroke with square ends, then cut level at y0, y1."""
    return band(pen_stroke([L(p0, p1)]), y0, y1)


def centre_stroke(p0, p1, y0, y1):
    """A straight stroke along the centre line p0-p1, cut level at y0 and y1."""
    u = unit((p1[0] - p0[0], p1[1] - p0[1]))
    n = (-u[1] * HW, u[0] * HW)
    e0 = (p0[0] + n[0], p0[1] + n[1])
    e1 = (p1[0] + n[0], p1[1] + n[1])
    return edge_stroke(e0, e1, 1, y0, y1)


def rotate180(path, cx, cy):
    out = pathops.Path()
    pen = out.getPen()

    class R:
        def moveTo(self, p): pen.moveTo((2 * cx - p[0], 2 * cy - p[1]))
        def lineTo(self, p): pen.lineTo((2 * cx - p[0], 2 * cy - p[1]))
        def curveTo(self, *ps): pen.curveTo(*[(2 * cx - x, 2 * cy - y) for x, y in ps])
        def qCurveTo(self, *ps): pen.qCurveTo(*[(2 * cx - x, 2 * cy - y) for x, y in ps])
        def closePath(self): pen.closePath()
        def endPath(self): pen.endPath()
    path.draw(R())
    return pathops.simplify(out, clockwise=True)


# ---------------------------------------------------------------- letters

def build(font):
    gs = font.getGlyphSet()
    cm = font.getBestCmap()
    m = measure(font)
    X = 528
    C = 700
    ASC = 738
    DSC = -190
    TAIL = -206
    os_l, os_c = 12, 15
    W = PEN

    def gname(ch):
        return cm[ord(ch)] if len(ch) == 1 else ch

    def box(ch):
        pts = [p for c in contours(font['glyf'][gname(ch)]) for p in c[0]]
        return bounds(pts)

    def stems(ch, y):
        """Centres of the ink runs at height y in the current glyph."""
        pen = Flat(gs)
        gs[gname(ch)].draw(pen)
        return [((a + b) / 2, b - a) for a, b in runs(pen.segs, True, y)]

    def arch_n(xl, xr, top_c, spring=None):
        """The n arch's centre line: up from the left stem, over, down the right."""
        cx, rx = (xl + xr) / 2, (xr - xl) / 2
        ry = spring if spring else rx * 1.0
        ys = top_c - ry
        return [L((xl, ys - 80), (xl, ys)), Q(cx, ys, rx, ry, 180, False), Q(cx, ys, rx, ry, 90, False),
                L((xr, ys), (xr, 0))]

    G = {}
    ADV = {}

    # ---- o c e
    x0, _, x1, _ = box('o')
    G['o'] = ring(x0, -os_l, x1, X + os_l)
    x0, _, x1, _ = box('c')
    cring = ring(x0, -os_l, x1 + 10, X + os_l)
    cx = (x0 + x1 + 10) / 2
    G['c'] = minus(cring, rect(cx, 0.30 * X, 3000, 0.70 * X))
    x0, _, x1, _ = box('e')
    ering = ring(x0, -os_l, x1, X + os_l)
    cx = (x0 + x1) / 2
    yb = 0.53 * X
    G['e'] = minus(union(ering, hbar(x0 + HW, x1 - HW, yb)), rect(cx, 0.25 * X, 3000, yb - HW))

    # ---- n h m u r
    for ch, top in (('n', X), ('h', ASC)):
        (xl, _), = stems(ch, 0.2 * X)[:1]
        xr = stems(ch, 0.2 * X)[-1][0]
        G[ch] = union(stem(xl, 0, top), pen_stroke(arch_n(xl, xr, X + 8 - HW)))
    s = stems('m', 0.2 * X)
    xl, xm, xr = s[0][0], s[1][0], s[2][0]
    G['m'] = union(stem(xl, 0, X), pen_stroke(arch_n(xl, xm, X + 8 - HW)), pen_stroke(arch_n(xm, xr, X + 8 - HW)))
    s = stems('u', 0.6 * X)
    xl, xr = s[0][0], s[-1][0]
    nlike = union(stem(xl, 0, X), pen_stroke(arch_n(xl, xr, X + 8 - HW)))
    G['u'] = rotate180(nlike, (xl + xr) / 2, X / 2)
    xl = stems('r', 0.2 * X)[0][0]
    _, _, rx1, _ = box('r')
    rr = 150
    arm = [L((xl, X + 8 - HW - rr - 80), (xl, X + 8 - HW - rr)), Q(xl + rr, X + 8 - HW - rr, rr, rr, 180, False),
           L((xl + rr, X + 8 - HW), (rx1 + 80, X + 8 - HW))]
    G['r'] = union(stem(xl, 0, X), minus(pen_stroke(arm), rect(rx1, 0, 3000, 3000)))

    # ---- i j l
    xi = stems('i', 0.2 * X)[0][0]
    G['i'] = stem(xi, 0, X)                    # dot kept from the font (already smaller)
    xj = stems('j', 0.2 * X)[0][0]
    _, _, _, _ = box('j')
    jx0 = box('j')[0]
    ry = 90
    rxj = xj - (jx0 + 18)
    tail = [L((xj, X), (xj, TAIL + HW + ry)), Q(xj - rxj, TAIL + HW + ry, rxj, ry, 0, False),
            L((xj - rxj, TAIL + HW), (jx0 - 60, TAIL + HW))]
    G['j'] = minus(pen_stroke(tail), rect(-3000, -3000, jx0, 0))
    xlc = stems('l', 0.2 * X)[0][0]
    G['l'] = stem(xlc, 0, ASC)

    # ---- b d p q g a
    x0, _, x1, _ = box('b')
    xs = stems('b', 0.5 * X)[0][0]
    G['b'] = union(stem(xs, 0, ASC), ring(xs - HW, -os_l, x1, X + os_l))
    x0, _, x1, _ = box('d')
    xs = stems('d', 0.5 * X)[-1][0]
    G['d'] = union(stem(xs, 0, ASC), ring(x0, -os_l, xs + HW, X + os_l))
    x0, _, x1, _ = box('p')
    xs = stems('p', -100)[0][0]
    G['p'] = union(stem(xs, DSC, X), ring(xs - HW, -os_l, x1, X + os_l))
    x0, _, x1, _ = box('q')
    xs = stems('q', -100)[0][0]
    G['q'] = union(stem(xs, DSC, X), ring(x0, -os_l, xs + HW, X + os_l))
    # g: the single-storey form, in g.ss03's place and width
    x0, _, x1, _ = box('g.ss03')
    xs = stems('g.ss03', 0.5 * X)[-1][0]
    bot = TAIL + HW
    cxt = (x0 + HW + xs) / 2
    rxt = xs - cxt
    hook = [L((xs, X), (xs, -40)), Q(cxt, -40, rxt, -40 - bot, 0, False),
            Q(cxt, bot + 85, rxt, 85, 270, False)]
    G['g'] = union(ring(x0, -os_l, xs + HW, X + os_l), pen_stroke(hook))
    ADV['g'] = font['hmtx']['g.ss03'][0]
    # a: two-storey, stem, top arc cut level at its left end, round bowl
    x0, _, x1, _ = box('a')
    xs = x1 - HW
    apex_x = (x0 + x1) / 2 - 6
    top_c = X + os_l - HW
    arc = [L((xs, 0.30 * X), (xs, 0.66 * X)),
           Q(apex_x, 0.66 * X, xs - apex_x, top_c - 0.66 * X, 0, True),
           Q(apex_x, 0.66 * X, apex_x - (x0 + HW + 4), top_c - 0.66 * X, 90, True)]
    arc = minus(pen_stroke(arc), rect(-3000, 0.0, apex_x - 30, 0.77 * X))
    G['a'] = union(stem(xs, 0, 0.66 * X), arc, ring(x0, -os_l, xs + HW, 0.60 * X))

    # ---- f t (narrower now), fi fl
    def f_shape(xs, bar0, bar1, x_term, arm_top):
        rf = 115
        arm = [L((xs, X), (xs, arm_top - HW - rf)), Q(xs + rf, arm_top - HW - rf, rf, rf, 180, False),
               L((xs + rf, arm_top - HW), (x_term + 80, arm_top - HW))]
        armp = minus(pen_stroke(arm), rect(x_term, X, 3000, 3000))
        return union(stem(xs, 0, X), armp, hbar(bar0, bar1, X - HW))
    xf = stems('f', 0.2 * X)[0][0]
    G['f'] = f_shape(xf, xf - 135, xf + 175, xf + 205, 753)
    ADV['f'] = round(xf + 205 + 25)
    xt = stems('t', 0.2 * X)[0][0]
    G['t'] = union(stem(xt, 0, 670), hbar(xt - 125, xt + 185, X - HW))
    ADV['t'] = round(xt + 185 + 35)
    xfi = stems('fi', 0.2 * X)[0][0]
    ifi = stems('fi', 0.2 * X)[-1]
    G['fi'] = union(f_shape(xfi, xfi - 135, ifi[0] + HW, ifi[0] + HW, 753), stem(ifi[0], 0, X))
    xfl = stems('fl', 0.2 * X)[0][0]
    lfl = stems('fl', 0.2 * X)[-1]
    G['fl'] = union(f_shape(xfl, xfl - 135, xfl + 175, lfl[0] - HW - 60, 753), stem(lfl[0], 0, ASC))

    # ---- k v w x y z
    def k_shape(xs, k1, top_arm, y_join, top_stem):
        arm = segment((k1 - 60 + 0.12 * (k1 - xs), top_arm + 60), (xs, y_join), 0, top_arm)
        jx, jy = xs + 0.42 * (k1 - 60 - xs), y_join + 0.42 * (top_arm - y_join)
        leg = segment((jx, jy), (k1 - 50 + 0.1 * (k1 - jx), -60), 0, top_arm)
        return union(stem(xs, 0, top_stem), arm, leg)
    xs = stems('k', 0.2 * X)[0][0]
    G['k'] = k_shape(xs, box('k')[2], X, 0.22 * X, ASC)

    # Points (v w y A V W): the two centre lines meet at the point, so the
    # strokes overlap evenly there and nothing sticks out.
    def vee(x0, x1, top, xv, yv, tail=None):
        xl, _ = inset(x0, 1, top, yv, xv)
        xr, _ = inset(x1, -1, top, yv, xv)
        left = centre_stroke((xl, top), (xv, yv), yv, top)
        right = centre_stroke((xr, top), (xv, yv), tail if tail is not None else yv, top)
        return union(left, right)
    x0, _, x1, _ = box('v')
    G['v'] = vee(x0, x1, X, (x0 + x1) / 2, 0)
    x0, _, x1, _ = box('y')
    G['y'] = vee(x0, x1, X, (x0 + x1) / 2 - 10, 0, tail=DSC)

    def w_shape(x0, x1, top, inner=0.27):
        b1 = x0 + inner * (x1 - x0)
        b2 = x1 - inner * (x1 - x0)
        cx = (x0 + x1) / 2
        xl, _ = inset(x0, 1, top, 0, b1)
        xr, _ = inset(x1, -1, top, 0, b2)
        return union(centre_stroke((xl, top), (b1, 0), 0, top), centre_stroke((b1, 0), (cx, top), 0, top),
                     centre_stroke((cx, top), (b2, 0), 0, top), centre_stroke((xr, top), (b2, 0), 0, top))
    x0, _, x1, _ = box('w')
    G['w'] = w_shape(x0, x1, X)

    def x_shape(x0, x1, top):
        a, _ = inset(x0, 1, top, 0, x1 - 60)
        b = x1 - (a - x0)
        return union(centre_stroke((a, top), (b, 0), 0, top), centre_stroke((b, top), (a, 0), 0, top))
    x0, _, x1, _ = box('x')
    G['x'] = x_shape(x0, x1, X)

    def z_shape(x0, x1, top):
        a, _ = inset(x1, -1, top - HW, HW, x0 + 60)
        b = x0 + (x1 - a)
        diag = centre_stroke((a, top - HW), (b, HW), HW, top - HW)
        return union(hbar(x0, x1, top - HW), hbar(x0, x1, HW), diag)
    x0, _, x1, _ = box('z')
    G['z'] = z_shape(x0, x1, X)

    # ---- s S
    def s_shape(L_, B_, R_, Tp):
        Hs = Tp - B_
        pts = [(R_ - 0.12 * (R_ - L_), B_ + 0.785 * Hs), ((L_ + R_) / 2 + 6, Tp - HW), (L_ + HW, B_ + 0.735 * Hs),
               ((L_ + R_) / 2, B_ + 0.508 * Hs), (R_ - HW, B_ + 0.255 * Hs), ((L_ + R_) / 2 - 6, B_ + HW),
               (L_ + 0.09 * (R_ - L_), B_ + 0.225 * Hs)]
        tan = [(-0.42, 0.91), (-1, 0), (0, -1), (1, -0.40), (0, -1), (-1, 0), (-0.42, 0.91)]
        return pen_stroke([H(pts[i], tan[i], pts[i + 1], tan[i + 1]) for i in range(6)])
    x0, _, x1, _ = box('s')
    G['s'] = s_shape(x0, -os_l, x1, X + os_l)
    x0, _, x1, _ = box('S')
    G['S'] = s_shape(x0, -os_c, x1, C + os_c)

    # ---- capitals with stems
    def capstems(ch, y=0.2 * C):
        return [c for c, w in stems(ch, y)]
    s = capstems('E')
    x0, _, x1, _ = box('E')
    G['E'] = union(stem(s[0], 0, C), hbar(s[0], x1, C - HW), hbar(s[0], s[0] + 0.78 * (x1 - s[0]), 0.51 * C),
                   hbar(s[0], x1, HW))
    s = capstems('F')
    x0, _, x1, _ = box('F')
    G['F'] = union(stem(s[0], 0, C), hbar(s[0], x1, C - HW), hbar(s[0], s[0] + 0.76 * (x1 - s[0]), 0.49 * C))
    s = capstems('H')
    G['H'] = union(stem(s[0], 0, C), stem(s[-1], 0, C), hbar(s[0], s[-1], 0.51 * C))
    G['I'] = stem(capstems('I')[0], 0, C)
    s = capstems('L')
    _, _, x1, _ = box('L')
    G['L'] = union(stem(s[0], 0, C), hbar(s[0], x1, HW))
    _, _, x1, _ = box('T')
    x0 = box('T')[0]
    G['T'] = union(hbar(x0, x1, C - HW), stem(capstems('T')[0], 0, C))
    s = capstems('N')
    G['N'] = union(stem(s[0], 0, C), stem(s[-1], 0, C), centre_stroke((s[0], C), (s[-1], 0), 0, C))
    s = capstems('M', 0.85 * C)
    x0, _, x1, _ = box('M')
    ml, mr = s[0], s[-1]
    cxm = (ml + mr) / 2
    G['M'] = union(stem(ml, 0, C), stem(mr, 0, C), centre_stroke((ml + 20, C), (cxm, 0), 0, C),
                   centre_stroke((mr - 20, C), (cxm, 0), 0, C))
    G['K'] = k_shape(capstems('K')[0], box('K')[2], C, 0.30 * C, C)
    # U J
    x0, _, x1, _ = box('U')
    xl, xr = x0 + HW, x1 - HW
    cxu, rxu = (xl + xr) / 2, (xr - xl) / 2
    ryu = rxu * 0.92
    yu = -11 + HW + ryu
    G['U'] = pen_stroke([L((xl, C), (xl, yu)), Q(cxu, yu, rxu, ryu, 180, True), Q(cxu, yu, rxu, ryu, 270, True),
                         L((xr, yu), (xr, C))])
    x0, _, x1, _ = box('J')
    xr = x1 - HW
    cxj = (x0 + HW + xr) / 2
    rxj = xr - cxj
    ryj = rxj
    yj = -10 + HW + ryj
    G['J'] = pen_stroke([L((xr, C), (xr, yj)), Q(cxj, yj, rxj, ryj, 0, False), Q(cxj, yj, rxj, ryj, 270, False)])

    # ---- A V W X Y Z
    x0, _, x1, _ = box('A')
    cxa = (x0 + x1) / 2
    xl, _ = inset(x0, 1, 0, C, cxa)
    xr = x1 - (xl - x0)
    yb = 0.30 * C
    bl = xl + (cxa - xl) * yb / C
    G['A'] = union(centre_stroke((xl, 0), (cxa, C), 0, C), centre_stroke((xr, 0), (cxa, C), 0, C),
                   hbar(bl, 2 * cxa - bl, yb))
    x0, _, x1, _ = box('V')
    G['V'] = vee(x0, x1, C, (x0 + x1) / 2, 0)
    x0, _, x1, _ = box('W')
    G['W'] = w_shape(x0, x1, C, inner=0.26)
    x0, _, x1, _ = box('X')
    G['X'] = x_shape(x0, x1, C)
    # Y: arms whose outer edges run into the stem's edges, trimmed to that outline
    x0, _, x1, _ = box('Y')
    cxy = (x0 + x1) / 2
    yj = 0.42 * C
    arms = union(edge_stroke((x0, C), (cxy - HW, yj), -1, yj, C), edge_stroke((x1, C), (cxy + HW, yj), 1, yj, C))
    arms = pathops.op(arms, poly([(x0, C), (x1, C), (cxy + HW, yj), (cxy - HW, yj)]),
                      pathops.PathOp.INTERSECTION, clockwise=True)
    G['Y'] = union(arms, stem(cxy, 0, yj + 2))
    x0, _, x1, _ = box('Z')
    G['Z'] = z_shape(x0, x1, C)

    # ---- O C G Q D P B R
    x0, _, x1, _ = box('O')
    G['O'] = ring(x0, -os_c, x1, C + os_c)
    G['Q'] = union(G['O'], segment((x0 + 0.58 * (x1 - x0), 0.20 * C), (x1 + 30, -160), -136, C))
    ADV['Q'] = font['hmtx']['O'][0] + 10
    x0, _, x1, _ = box('C')
    cring = ring(x0, -os_c, x1 + 22, C + os_c)
    cxc = (x0 + x1 + 22) / 2
    G['C'] = minus(cring, rect(cxc, 0.36 * C, 3000, 0.66 * C))
    x0, _, x1, _ = box('G')
    gring = ring(x0, -os_c, x1, C + os_c)
    cxg = (x0 + x1) / 2
    yg = 0.44 * C
    G['G'] = union(minus(gring, rect(cxg, yg, 3000, 0.66 * C)), hbar(cxg + 40, x1, yg), rect(x1 - W, 0, x1, yg + HW))

    def bowl(xs, ytop, ybot, xright):
        """A D/P/B bowl's centre line from the stem at ytop round to the stem at ybot."""
        ry = (ytop - ybot) / 2
        rx = min(ry * 1.05, (xright - HW) - xs - 20)
        xa = xright - HW - rx
        yc = (ytop + ybot) / 2
        return pen_stroke([L((xs, ytop), (xa, ytop)), Q(xa, yc, rx, ry, 90, False), Q(xa, yc, rx, ry, 0, False),
                           L((xa, ybot), (xs, ybot))])
    s = capstems('D')
    _, _, x1, _ = box('D')
    G['D'] = union(stem(s[0], 0, C), bowl(s[0], C - HW, HW, x1))
    s = capstems('P')
    _, _, x1, _ = box('P')
    G['P'] = union(stem(s[0], 0, C), bowl(s[0], C - HW, 0.37 * C + HW, x1))
    s = capstems('B')
    _, _, x1, _ = box('B')
    ym = 0.535 * C
    G['B'] = union(stem(s[0], 0, C), bowl(s[0], C - HW, ym, x1 - 32), bowl(s[0], ym, HW, x1))
    s = capstems('R')
    _, _, x1, _ = box('R')
    rb = x1 - 18
    ybar = 0.37 * C + HW
    xt = s[0] + 0.42 * (rb - s[0])
    xr = rb - 10
    wh = W
    for _ in range(6):
        th = math.atan2(ybar, (xr - wh / 2) - xt)
        wh = W / math.sin(th)
    leg = poly([(xt - wh / 2, ybar), (xt + wh / 2, ybar), (xr, 0), (xr - wh, 0)])
    G['R'] = union(stem(s[0], 0, C), bowl(s[0], C - HW, ybar, rb), leg)

    # ---- figures
    x0, _, x1, _ = box('0')
    G['zero'] = ring(x0, -11, x1, C + 11, k=0.62)
    x0, _, x1, _ = box('1')
    xs1 = x1 - HW
    G['one'] = union(stem(xs1, 0, C), segment((xs1, C - HW * 0.7), (x0 + 40, C - 0.22 * C), -3000, C))
    x0, _, x1, _ = box('2')
    cx2 = (x0 + x1) / 2
    ry2 = 0.165 * C
    yc2 = C + 10 - HW - ry2
    top = [Q(cx2, yc2, cx2 - x0 - HW, ry2, 180, False), Q(cx2, yc2, x1 - HW - cx2, ry2, 90, False),
           H((x1 - HW, yc2), (0, -1), (x0 + HW + 15, HW + 30), (-0.62, -0.78), k=0.45)]
    G['two'] = union(pen_stroke(top), hbar(x0, x1, HW))
    x0, _, x1, _ = box('3')
    cx3 = (x0 + x1) / 2 - 10
    yw = 0.535 * C
    up_r = 0.205 * C
    upper = [Q(cx3, C + 10 - HW - up_r, cx3 - x0 - HW, up_r, 180, False),
             Q(cx3, C + 10 - HW - up_r, x1 - HW - 25 - cx3, up_r, 90, False),
             H((x1 - HW - 25, C + 10 - HW - up_r), (0, -1), (cx3 - 30, yw), (-1, 0), k=0.40),
             L((cx3 - 30, yw), (cx3 - 110, yw))]
    lo_r = (yw - (-10 + HW)) / 2
    lower = [L((cx3 - 110, yw), (cx3, yw)), Q(cx3, yw - lo_r, x1 - HW - cx3, lo_r, 90, False),
             Q(cx3, yw - lo_r, x1 - HW - cx3, lo_r, 0, False),
             H((cx3, -10 + HW), (-1, 0), (x0 + HW, 0.22 * C), (-0.25, 0.97), k=0.45)]
    G['three'] = union(pen_stroke(upper), pen_stroke(lower))
    x0, _, x1, _ = box('4')
    xs4 = x1 - 0.24 * (x1 - x0)
    yb4 = 0.27 * C
    xd, _ = inset(x0, 1, yb4, C, xs4)
    diag4 = minus(centre_stroke((xd, yb4), (xs4, C), yb4, C), rect(xs4 + HW, -3000, 3000, 3000))
    G['four'] = union(stem(xs4, 0, C), hbar(x0, x1, yb4), diag4)
    x0, _, x1, _ = box('5')
    xv = x0 + HW + 25
    yb5 = 0.60 * C
    r5 = (yb5 - (-10)) / 2
    cx5 = (xv + x1 - HW) / 2 + 10
    bowl5 = [H((xv, 0.53 * C), (0.85, 0.53), (cx5, yb5 - HW), (1, 0), k=0.45),
             Q(cx5, yb5 - r5, x1 - HW - cx5, r5 - HW, 90, False), Q(cx5, yb5 - r5, x1 - HW - cx5, r5 - HW, 0, False),
             H((cx5, -10 + HW), (-1, 0), (x0 + HW, 0.20 * C), (-0.30, 0.95), k=0.45)]
    G['five'] = union(pen_stroke(bowl5), stem(xv, 0.53 * C, C), hbar(xv - HW, x1, C - HW))
    x0, _, x1, _ = box('6')
    y6 = 0.63 * C
    low6 = ring(x0, -10, x1, y6)
    cx6 = (x0 + x1) / 2
    r6 = (C + 9 - HW) - 0.35 * C
    up6 = [L((x0 + HW, 0.25 * C), (x0 + HW, 0.35 * C)), Q(cx6 + 20, 0.35 * C, cx6 + 20 - x0 - HW, r6, 180, False),
           Q(cx6 + 20, 0.35 * C, x1 - HW - cx6 - 20, r6, 90, False)]
    up6 = minus(pen_stroke(up6), rect(cx6, 0.20 * C, 3000, 0.80 * C))
    G['six'] = union(low6, up6)
    x0, _, x1, _ = box('9')
    G['nine'] = rotate180(G['six'], (x0 + x1) / 2 if False else (box('6')[0] + box('6')[2]) / 2, C / 2)
    shift9 = (x0 + x1) / 2 - (box('6')[0] + box('6')[2]) / 2
    G['nine'] = _shift(G['nine'], shift9, 0)
    x0, _, x1, _ = box('7')
    xb7 = x0 + 0.33 * (x1 - x0)
    xt7, _ = inset(x1, -1, C - HW, 0, xb7)
    G['seven'] = union(hbar(x0, x1, C - HW), centre_stroke((xt7, C - HW), (xb7, 0), 0, C - HW))
    x0, _, x1, _ = box('8')
    G['eight'] = union(ring(x0, -10, x1, 0.555 * C + HW), ring(x0 + 32, 0.555 * C - HW, x1 - 32, C + 10))
    return G, ADV


def _shift(path, dx, dy):
    out = pathops.Path()
    pen = out.getPen()

    class S:
        def moveTo(self, p): pen.moveTo((p[0] + dx, p[1] + dy))
        def lineTo(self, p): pen.lineTo((p[0] + dx, p[1] + dy))
        def curveTo(self, *ps): pen.curveTo(*[(x + dx, y + dy) for x, y in ps])
        def qCurveTo(self, *ps): pen.qCurveTo(*[(x + dx, y + dy) for x, y in ps])
        def closePath(self): pen.closePath()
        def endPath(self): pen.endPath()
    path.draw(S())
    return out


# ---------------------------------------------------------------- main

def main():
    global PEN, HW
    ap = argparse.ArgumentParser()
    ap.add_argument('--weight', type=float, default=100)
    ap.add_argument('--dot', type=float, default=0.79)
    args = ap.parse_args()
    PEN, HW = args.weight, args.weight / 2

    font = inst(400)
    stem_w = measure(font)['stem']
    dots = smaller_dots(font, args.dot)
    print(f'pen {PEN:g}; smaller dots in {len(dots)} glyphs')
    G, ADV = build(font)

    cm = font.getBestCmap()
    rebuilt = set()
    for key, path in G.items():
        name = cm.get(ord(key), key) if len(key) == 1 else key
        if name in ('fi', 'fl'):
            set_glyph(font, name, path)
            rebuilt.add(name)
            continue
        only = None
        if name in ('i', 'j'):
            # keep the (already smaller) dot; swap the stem and tail only
            only = (lambda pts: bounds(pts)[1] < 400)
            if name == 'i':
                path = G['i']
        done, skipped = apply_family(font, name, path, ADV.get(name), only=only)
        rebuilt.update(done)
        if skipped:
            print(f'{name}: not matched: {" ".join(skipped)}')
    # the single-storey g is now the default; its stylistic-set copies match it
    import copy
    for n in list(font.getGlyphOrder()):
        if n.endswith('.ss03') and n[:-5] in rebuilt:
            font['glyf'][n] = copy.deepcopy(font['glyf'][n[:-5]])
            font['hmtx'][n] = font['hmtx'][n[:-5]]
            rebuilt.add(n)
    print(f'redrawn: {len(rebuilt)} glyphs')

    merged = 0
    for name in font.getGlyphOrder():
        g = font['glyf'][name]
        if g.isComposite() or g.numberOfContours <= 1:
            continue
        set_glyph(font, name, pathops.simplify(to_path(g, font['glyf']), clockwise=True))
        merged += 1
    rest = even_strokes(font, stem_w, PEN / stem_w, {}, skip=rebuilt)
    print(f'overlaps merged in {merged}; even-stroke pass on {len(rest)} other glyphs')

    glyf, hmtx = font['glyf'], font['hmtx']
    for name in font.getGlyphOrder():
        glyf[name].recalcBounds(glyf)
        hmtx[name] = (hmtx[name][0], getattr(glyf[name], 'xMin', 0))
    rename(font, 'AA Bridge Sans Text Step3')
    out = os.path.join(HERE, 'fonts', 'AABridgeSansTextStep3-Regular.ttf')
    font.save(out)
    print('wrote', os.path.relpath(out))


PEN, HW = 100.0, 50.0

if __name__ == '__main__':
    main()
