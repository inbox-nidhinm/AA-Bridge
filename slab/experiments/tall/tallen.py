"""Experiment: AA Bridge Slab 20% taller, Regular display only, a few key letters.

usage: tallen.py SRC.glyphs OUT.glyphs [--method compensated|plain|none]
                 [--scale 1.2] [--glyphs HORSAandglovesxpy]

Only the Regular display drawing ({378,144} brace layer) of the listed
letters is changed, so a Regular build of OUT shows the experiment while
spacing, kerning and every other glyph stay exactly as released.

compensated (the real one): stroke-weight compensated scaling, the method
    behind RMX Scaler / ScaleFast. Each point keeps its x from the Regular
    drawing (so stems, serif lengths and widths are untouched) and takes its
    y from an interpolation between Thin and Regular whose horizontal strokes
    are Regular / scale thick, then that y is scaled. Horizontal strokes come
    back at exactly Regular thickness, and because both the horizontal and the
    vertical cross-sections of every stroke are kept, diagonals and the S
    spine keep their weight too. Curves are scaled, not bent, so bowls stay
    round instead of going boxy.
plain: every y times scale (the naive stretch, for comparison only).
none: copy (for an exact like-for-like original build).

Caps (and anything reaching cap height) are scaled so cap height is exactly
scale x 700. Lowercase is scaled so the x-height is exactly scale x Regular
x-height; ascenders and descenders follow the same factor. Smooth nodes are
re-aligned after the move so no curve gets a kink, and all coordinates are
integers. Where an overlapping piece (a serif, a bracket) has a node sitting
on another contour's edge, that node is put back on the moved edge, so the
merged outline gets no little steps.

Rebuild everything (from the repo root, with fontmake and friends installed;
outputs go to build/, which git ignores):

  D=slab/experiments/tall
  python $D/tallen.py slab/sources/AABridgeSlab.glyphs build/tall/compensated.glyphs
  python $D/tallen.py slab/sources/AABridgeSlab.glyphs build/tall/plain.glyphs --method plain
  python heighten.py slab/sources/AABridgeSlab.glyphs build/tall/bands.glyphs \\
      --x 20 --cap 140 --asc-ratio 1.043          # Montagu Slab/tools/heighten.py
  for v in compensated plain bands; do
    fontmake -g build/tall/$v.glyphs -i "AA Bridge Slab Regular" -o otf --output-dir build/tall/$v
  done
  fontmake -g slab/sources/AABridgeSlab.glyphs -i "AA Bridge Slab Regular" -o otf --output-dir build/tall/original
  R=AABridgeSlab-Regular.otf
  python $D/check.py build/tall/{original,plain,bands,compensated}/$R
  python $D/board.py build/tall/original/$R build/tall/compensated/$R $D/board build/tall/plain/$R build/tall/bands/$R
  python $D/testfont.py build/tall/compensated/$R $D/AABridgeSlabTallTest-Regular.otf
"""
import argparse
import math

import glyphsLib
import pathops

REG, THIN = '{378,144}', 'Thin'
CORNER = 5  # degrees: a "smooth" node turning more than this is a drawn corner


def layers(g):
    return {l.name: l for l in g.layers}


def to_path(layer):
    p = pathops.Path()
    pen = p.getPen()
    for c in layer.paths:
        nodes = list(c.nodes)
        k = max(i for i, n in enumerate(nodes) if n.type != 'offcurve')
        seq = nodes[k + 1:] + nodes[:k + 1]
        pen.moveTo(tuple(seq[-1].position))
        buf = []
        for n in seq:
            if n.type == 'offcurve':
                buf.append(tuple(n.position))
            else:
                pen.curveTo(*buf, tuple(n.position)) if buf else pen.lineTo(tuple(n.position))
                buf = []
        pen.closePath()
    p.simplify()
    return p


def vertical_runs(layer, x):
    """ink thicknesses along the vertical line at x, bottom to top"""
    r = pathops.Path()
    pen = r.getPen()
    pen.moveTo((x - .5, -500)); pen.lineTo((x + .5, -500)); pen.lineTo((x + .5, 1500)); pen.lineTo((x - .5, 1500)); pen.closePath()
    out = []
    for c in pathops.op(to_path(layer), r, pathops.PathOp.INTERSECTION).contours:
        ys = [pt[1] for s in c.segments for pt in s[1]]
        out.append((min(ys), max(ys) - min(ys)))
    return [h for _, h in sorted(out)]


def light_t(font, scale):
    """Thin->Regular interpolation factor whose horizontal strokes are
    Regular / scale thick, from the H bar, o and O hairlines and n serif."""
    samples = []
    for name, x in (('H', None), ('o', None), ('O', None), ('n', 40)):
        L = layers(font.glyphs[name])
        at = lambda k: x if x is not None else L[k].width / 2   # glyph centre, or a fixed x
        samples += zip(vertical_runs(L[THIN], at(THIN)), vertical_runs(L[REG], at(REG)))
    ts = [(reg / scale - thin) / (reg - thin) for thin, reg in samples]
    return sum(ts) / len(ts), samples


def segments(path):
    """[(node indices of the segment: start, [offcurves...], end)] of a closed path"""
    nodes = list(path.nodes)
    N = len(nodes)
    ons = [i for i, n in enumerate(nodes) if n.type != 'offcurve']
    out = []
    for k, i in enumerate(ons):
        j = ons[(k + 1) % len(ons)]
        idx = [(i + d) % N for d in range(1, (j - i) % N + 1)]
        out.append([i] + idx)
    return out


def bez(pts, t):
    """point and tangent of a line (2 pts) or cubic (4 pts) at t"""
    if len(pts) == 2:
        (x0, y0), (x1, y1) = pts
        return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), (x1 - x0, y1 - y0)
    p0, p1, p2, p3 = pts
    m = 1 - t
    pt = tuple(m**3 * p0[i] + 3 * m * m * t * p1[i] + 3 * m * t * t * p2[i] + t**3 * p3[i] for i in (0, 1))
    tg = tuple(3 * m * m * (p1[i] - p0[i]) + 6 * m * t * (p2[i] - p1[i]) + 3 * t * t * (p3[i] - p2[i]) for i in (0, 1))
    return pt, tg


def seg_pts(path, seg):
    nodes = list(path.nodes)
    return [(nodes[i].position.x, nodes[i].position.y) for i in seg]


def closest(pts, p, steps=200):
    """parameter and distance of the point on a segment closest to p"""
    best = (0.0, float('inf'))
    for s in range(steps + 1):
        t = s / steps
        q, _ = bez(pts, t)
        d = math.dist(p, q)
        if d < best[1]:
            best = (t, d)
    t0, lo, hi = best[0], max(0.0, best[0] - 1 / steps), min(1.0, best[0] + 1 / steps)
    for _ in range(30):                     # refine by ternary search
        a, b = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if math.dist(p, bez(pts, a)[0]) < math.dist(p, bez(pts, b)[0]):
            hi = b
        else:
            lo = a
    t0 = (lo + hi) / 2
    return t0, math.dist(p, bez(pts, t0)[0])


def find_joins(layer, tol=0.75):
    """Nodes of one contour that sit on an edge of another contour (where an
    overlapping piece such as a bracket or serif meets a stroke):
    [(path i, node n, path j, segment, t, handle-follows-edge)]"""
    joins = []
    paths = list(layer.paths)
    for i, p in enumerate(paths):
        nodes = list(p.nodes)
        for n, node in enumerate(nodes):
            if node.type == 'offcurve':
                continue
            pos = (node.position.x, node.position.y)
            for j, q in enumerate(paths):
                if j == i:
                    continue
                for seg in segments(q):
                    pts = seg_pts(q, seg)
                    if pos in (pts[0], pts[-1]):
                        break                  # node on node: both move alike
                    t, d = closest(pts, pos)
                    if d <= tol and 0 < t < 1:
                        # does an adjacent handle run along the edge here?
                        _, tg = bez(pts, t)
                        follows = []
                        for nb in (nodes[n - 1], nodes[(n + 1) % len(nodes)]):
                            if nb.type == 'offcurve':
                                v = (nb.position.x - pos[0], nb.position.y - pos[1])
                                cross = (v[0] * tg[1] - v[1] * tg[0]) / (math.hypot(*v) * math.hypot(*tg) or 1)
                                follows.append(abs(cross) < 0.03)
                            else:
                                follows.append(False)
                        joins.append((i, n, j, seg, t, follows))
                        break
                else:
                    continue
                break
    return joins


def snap_joins(layer, joins):
    """Re-seat each join node on its edge after the move, with handles that
    followed the edge turned to follow it again, and round it to the
    integer point nearest the edge."""
    paths = list(layer.paths)
    for i, n, j, seg, t, follows in joins:
        nodes = list(paths[i].nodes)
        pts = seg_pts(paths[j], seg)
        node = nodes[n]
        here = (node.position.x, node.position.y)
        t, _ = closest(pts, here)
        (x, y), tg = bez(pts, t)
        # integer point nearest the edge
        cands = [(math.floor(x) + dx, math.floor(y) + dy) for dx in (0, 1) for dy in (0, 1)]
        node.position.x, node.position.y = min(cands, key=lambda c: (closest(pts, c)[1], math.dist(c, (x, y))))
        L = math.hypot(*tg) or 1
        u = (tg[0] / L, tg[1] / L)
        for nb, f in zip((nodes[n - 1], nodes[(n + 1) % len(nodes)]), follows):
            if not f:
                continue
            v = (nb.position.x - node.position.x, nb.position.y - node.position.y)
            along = v[0] * u[0] + v[1] * u[1]
            nb.position.x = round(node.position.x + u[0] * along)
            nb.position.y = round(node.position.y + u[1] * along)


def realign_smooth(path, skip=()):
    """Put the handles of every smooth node back on one line through it.
    Nodes in `skip` (flagged smooth but drawn as a real corner) are left."""
    nodes = list(path.nodes)
    N = len(nodes)
    for i, n in enumerate(nodes):
        if n.type == 'offcurve' or not n.smooth or i in skip:
            continue
        a, b = nodes[i - 1], nodes[(i + 1) % N]
        p = n.position
        va = (p.x - a.position.x, p.y - a.position.y)
        vb = (b.position.x - p.x, b.position.y - p.y)
        la, lb = math.hypot(*va), math.hypot(*vb)
        if not la or not lb:
            continue
        if a.type != 'offcurve' and b.type != 'offcurve':
            continue
        if a.type != 'offcurve':          # line in, handle out: follow the line
            d = (va[0] / la, va[1] / la)
        elif b.type != 'offcurve':        # handle in, line out
            d = (vb[0] / lb, vb[1] / lb)
        else:
            d = (va[0] / la + vb[0] / lb, va[1] / la + vb[1] / lb)
            m = math.hypot(*d)
            d = (d[0] / m, d[1] / m)
        if a.type == 'offcurve':
            a.position.x, a.position.y = p.x - d[0] * la, p.y - d[1] * la
        if b.type == 'offcurve':
            b.position.x, b.position.y = p.x + d[0] * lb, p.y + d[1] * lb


def kink(path):
    """largest angle (degrees) between the two sides of a smooth node"""
    return max(node_angles(path).values(), default=0.0)


def node_angles(path):
    """{node index: angle in degrees between its two sides} for smooth nodes"""
    nodes = list(path.nodes)
    out = {}
    for i, n in enumerate(nodes):
        if n.type == 'offcurve' or not n.smooth:
            continue
        a, b = nodes[i - 1], nodes[(i + 1) % len(nodes)]
        if a.type != 'offcurve' and b.type != 'offcurve':
            continue
        p = n.position
        u = (p.x - a.position.x, p.y - a.position.y)
        v = (b.position.x - p.x, b.position.y - p.y)
        if not math.hypot(*u) or not math.hypot(*v):
            continue
        out[i] = abs(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--method', default='compensated', choices=('compensated', 'plain', 'none'))
    ap.add_argument('--scale', type=float, default=1.2)
    ap.add_argument('--glyphs', default='HORSAandglovesxpy')
    a = ap.parse_args()

    font = glyphsLib.GSFont(a.src)
    t, samples = light_t(font, a.scale)
    if a.method == 'compensated':
        print(f'horizontal strokes Thin/Regular {samples}')
        print(f'light instance: {t:.3f} of the way Thin -> Regular')

    def tops(name):
        L = layers(font.glyphs[name])
        return [max(n.position.y for p in L[k].paths for n in p.nodes) for k in (THIN, REG)]

    # flat-topped references: cap height from H, x-height from x
    cap_thin, cap_reg = tops('H')
    xh_thin, xh_reg = tops('x')
    s_cap = a.scale * cap_reg / (cap_thin + (cap_reg - cap_thin) * t)
    s_low = a.scale * xh_reg / (xh_thin + (xh_reg - xh_thin) * t)

    by_char = {chr(int(g.unicode, 16)): g for g in font.glyphs if g.unicode}
    for ch in dict.fromkeys(a.glyphs):
        g = by_char[ch]
        L = layers(g)
        thin, reg = L[THIN], L[REG]
        upper = ch.isupper() or ch.isdigit()
        if a.method == 'plain':
            s, t_g = a.scale, 1.0          # y = Regular y x scale
        elif a.method == 'compensated':
            s, t_g = (s_cap if upper else s_low), t
        else:
            s, t_g = 1.0, 1.0
        # smooth nodes that are really smooth (not drawn corners), per path
        smooth = [{i for i, ang in node_angles(p).items() if ang <= CORNER} for p in reg.paths]
        worst = lambda: max((node_angles(p)[i] for p, idx in zip(reg.paths, smooth) for i in idx), default=0.0)
        before = worst()
        lerp = lambda yt, yr: (yt + (yr - yt) * t_g) * s
        if a.method == 'none':
            continue
        joins = find_joins(reg)
        for pt, pr, keep in zip(thin.paths, reg.paths, smooth):
            for nt, nr in zip(pt.nodes, pr.nodes):
                nr.position.y = lerp(nt.position.y, nr.position.y)
            realign_smooth(pr, set(node_angles(pr)) - keep)
            for n in pr.nodes:
                n.position.x, n.position.y = round(n.position.x), round(n.position.y)
        snap_joins(reg, joins)
        off = max((closest(seg_pts(reg.paths[j], seg), tuple(reg.paths[i].nodes[n].position))[1]
                   for i, n, j, seg, _, _ in joins), default=0)
        for at, ar in zip(thin.anchors, reg.anchors):
            ar.position.y = round(lerp(at.position.y, ar.position.y))
        ys = [n.position.y for p in reg.paths for n in p.nodes]
        print(f'{ch} x{s:.4f}  top {max(ys)}  bottom {min(ys)}  '
              f'worst smooth-node angle {before:.2f} -> {worst():.2f} deg  '
              f'joins {len(joins)} (furthest off its edge {off:.2f}u)')
    font.save(a.out)


if __name__ == '__main__':
    main()
