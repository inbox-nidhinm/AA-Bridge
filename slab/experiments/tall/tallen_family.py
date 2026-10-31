"""AA Bridge Slab Tall: the whole family 20% taller, every glyph, every layer.

usage: tallen_family.py SRC.glyphs OUT.glyphs [--scale 1.2] [--family NAME]

The same stroke-weight compensated scaling as tallen.py (see there), done on
all four masters and both Regular brace layers so the family still
interpolates from Thin to Bold at both optical sizes:

- For every layer (weight w, optical size o) the reference weight w' is the
  one whose horizontal strokes are 1/scale as thick as at w, read off the
  H bar, the o and O hairlines and the n serif along Thin -> Regular -> Bold.
  For Thin, w' lies a little below Thin and is extrapolated along
  Thin -> Regular; for Regular it is the 0.747 point of the key-letter
  experiment; for Bold it lies between Regular and Bold.
- Each point keeps its x and takes its y from w' (per glyph, from that
  glyph's own Thin / Regular / Bold drawings), scaled so cap height is
  scale x 700 and, for lowercase, x-height is scale x that layer's x-height.
- Smooth nodes are realigned, nodes where an overlapping piece meets a
  stroke are re-seated on the stroke edge, coordinates are whole units.
- Master metrics, alignment zones and line-spacing parameters are scaled,
  and the family is renamed so it never clashes with AA Bridge Slab.

Advance widths, sidebearings and kerning are untouched.

Where overlapping pieces meet, tallen.py's join handling keeps them meeting
(nodes on an edge, wedge and throat corners inside two edges, bracket
tips); any pinhole left is closed by nudging a small piece's node at most
NUDGE units. The S and s spines (which the compensation leaves a few units
light) are measured and set back to their drawn thickness.

Rebuild the family (from the repo root, fontmake and friends installed;
build/ is ignored by git):

  D=slab/experiments/tall
  python $D/tallen_family.py slab/sources/AABridgeSlab.glyphs build/tall/AABridgeSlabTall.glyphs
  fontmake -g build/tall/AABridgeSlabTall.glyphs -o variable --no-optimize-gvar \\
      --output-dir build/tall/family/variable
  fontmake -g build/tall/AABridgeSlabTall.glyphs -i -o otf --output-dir build/tall/family/otf
  python $D/cleanstatic.py build/tall/family/otf/*.otf
  # checks against the released AA Bridge Slab
  python $D/check_family.py 'slab/fonts/variable/AABridgeSlab[opsz,wght].ttf' \\
      build/tall/family/variable/AABridgeSlabTall-VF.ttf
  python $D/check_static.py slab/fonts/otf build/tall/family/otf
  # Figma board SVGs, one pair per display weight
  python $D/boardsvg_tall.py build/tall/family/otf/AABridgeSlabTall-Regular.otf Regular-line.svg Regular-grid.svg
"""
import argparse
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import math  # noqa: E402

import glyphsLib  # noqa: E402
import pathops  # noqa: E402
from glyphsLib.glyphdata import get_glyph  # noqa: E402

from tallen import (CORNER, _area, find_joins, node_angles, realign_smooth,  # noqa: E402
                    snap_joins, vertical_runs)

LINE_PARAMS = ('typoAscender', 'hheaAscender', 'typoDescender', 'hheaDescender', 'winAscent', 'winDescent')
HOLE = 2000   # units²: a new closed space smaller than this is a pinhole, not a counter
NUDGE = 6     # units: the furthest a node is moved to close a pinhole (never visibly)


def union(paths):
    """the layer's pieces merged, as pathops contours"""
    p = pathops.Path()
    pen = p.getPen()
    for c in paths:
        nodes = list(c.nodes)
        k = max(i for i, n in enumerate(nodes) if n.type != 'offcurve')
        seq = nodes[k + 1:] + nodes[:k + 1]
        pen.moveTo((seq[-1].position.x, seq[-1].position.y))
        buf = []
        for n in seq:
            if n.type == 'offcurve':
                buf.append((n.position.x, n.position.y))
            else:
                pen.curveTo(*buf, (n.position.x, n.position.y)) if buf else pen.lineTo((n.position.x, n.position.y))
                buf = []
        pen.closePath()
    p.simplify()
    return list(p.contours)


def contour_area(c):
    pts = [pt for s in c.segments for pt in s[1]]
    return _area(pts), pts


SPINES = {'S', 'Sacute', 'Scaron', 'Scedilla', 'Scircumflex', 'uni0218', 'uni1E60', 'uni1E62',
          's', 'sacute', 'scaron', 'scedilla', 'scircumflex', 'uni0219', 'uni1E61', 'uni1E63', 'dollar'}


def _runs(path, axis, at):
    """ink runs [(start, length)] of a pathops path along y=at ('h') or x=at ('v')"""
    r = pathops.Path()
    pen = r.getPen()
    pts = (((-500, at - .5), (2500, at - .5), (2500, at + .5), (-500, at + .5)) if axis == 'h' else
           ((at - .5, -800), (at + .5, -800), (at + .5, 1800), (at - .5, 1800)))
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()
    out = []
    for c in pathops.op(path, r, pathops.PathOp.INTERSECTION).contours:
        v = [pt[0 if axis == 'h' else 1] for s in c.segments for pt in s[1]]
        out.append((min(v), max(v) - min(v)))
    return sorted(out)


def spine_width(paths):
    """S spine thickness at the glyph's centre, from its upright and level
    cross-sections (the same measure as check.py)"""
    p = pathops.Path()
    for c in union(paths):
        c.draw(p.getPen())
    xs = [pt[0] for c in p.contours for s in c.segments for pt in s[1]]
    ys = [pt[1] for c in p.contours for s in c.segments for pt in s[1]]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    mid = min(_runs(p, 'v', cx), key=lambda r: abs(r[0] + r[1] / 2 - cy))
    yc = mid[0] + mid[1] / 2
    h = min(_runs(p, 'h', yc), key=lambda r: abs(r[0] + r[1] / 2 - cx))
    return 1 / math.sqrt(1 / h[1] ** 2 + 1 / mid[1] ** 2)


class _Pts:
    """stand-in for a GSPath built from saved node positions"""
    class N:
        def __init__(self, x, y, kind):
            self.position = type('P', (), {'x': x, 'y': y})()
            self.type = kind

    def __init__(self, pts, kinds):
        self.nodes = [self.N(x, y, k) for (x, y), k in zip(pts, kinds)]


def fix_spine(layer, orig):
    """The S spine is the one stroke the compensation leaves light (a
    shallow diagonal: its height across shrinks with the lighter reference
    weight more than the hairlines do). Measure it in the drawing and in the
    tall version, then move the flat top and bottom pieces of the spine
    (the on-curve nodes nearest the middle, above and below, with their
    handles) apart vertically until it measures as drawn. Returns
    (drawn, tall before, tall after)."""
    kinds = [[n.type for n in p.nodes] for p in layer.paths]
    drawn = spine_width([_Pts(o, k) for o, k in zip(orig, kinds)])
    before = spine_width(layer.paths)
    m = max(range(len(orig)), key=lambda i: abs(_area(orig[i])))
    path = layer.paths[m]
    t = [(n.position.x, n.position.y) for n in path.nodes]
    xs, ys = [p[0] for p in t], [p[1] for p in t]
    cx, cy, W, H = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)
    mids = [k for k, p in enumerate(t) if kinds[m][k] != 'offcurve'
            and abs(p[0] - cx) < 0.3 * W and abs(p[1] - cy) < 0.2 * H]
    up = [k for k in mids if t[k][1] > cy]
    down = [k for k in mids if t[k][1] < cy]
    if not up or not down or abs(drawn - before) < 0.5:
        return drawn, before, before

    def move(d):
        for group, sign in ((up, 1), (down, -1)):
            for k in group:
                for kk in {k - 1 if kinds[m][k - 1] == 'offcurve' else k, k,
                           (k + 1) % len(t) if kinds[m][(k + 1) % len(t)] == 'offcurve' else k}:
                    path.nodes[kk].position.y = round(t[kk][1] + sign * d / 2)
        return spine_width(layer.paths)

    # secant search on the vertical spread
    d0, w0 = 0.0, before
    d1 = (drawn - before) * 2
    w1 = move(d1)
    for _ in range(4):
        if abs(w1 - drawn) < 0.5 or w1 == w0:
            break
        d0, w0, d1 = d1, w1, d1 + (drawn - w1) * (d1 - d0) / (w1 - w0)
        w1 = move(d1)
    return drawn, before, w1


def repair_pinholes(layer, want):
    """After the move, a crotch wedge or bracket can leave a pinhole where
    it no longer quite covers the join between two strokes. While the
    merged layer has more contours than the drawing (`want`), take the
    smallest new closed space and nudge the nearest node of a small piece
    towards it, a unit at a time, until it closes. Returns the nudges."""
    done = []
    for _ in range(6):
        cs = union(layer.paths)
        if len(cs) <= want:
            break
        holes = sorted((abs(a), pts) for a, pts in map(contour_area, cs) if abs(a) < HOLE)
        if not holes:
            break
        _, pts = holes[0]
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        areas = [abs(_area([(n.position.x, n.position.y) for n in p.nodes])) for p in layer.paths]
        biggest = max(areas)
        cands = []
        for i, p in enumerate(layer.paths):
            if areas[i] == biggest:
                continue
            for k, n in enumerate(p.nodes):
                if n.type != 'offcurve':
                    d = math.dist((n.position.x, n.position.y), (cx, cy))
                    if d < 60:
                        cands.append((d, i, k))
        fixed = False
        for d, i, k in sorted(cands)[:8]:
            n = layer.paths[i].nodes[k]
            x0, y0 = n.position.x, n.position.y
            ux, uy = (cx - x0) / (d or 1), (cy - y0) / (d or 1)
            for step in range(1, NUDGE + 1):
                n.position.x, n.position.y = round(x0 + ux * step), round(y0 + uy * step)
                if len(union(layer.paths)) < len(cs):
                    done.append((i, k, (x0, y0), (n.position.x, n.position.y)))
                    fixed = True
                    break
            if fixed:
                break
            n.position.x, n.position.y = x0, y0
        if not fixed:
            break
    return done


def location(layer, masters):
    if layer.layerId == layer.associatedMasterId:
        return tuple(float(v) for v in masters[layer.layerId].axes)
    return tuple(float(v) for v in layer.name.strip('{}').split(','))


def segment(weights, w):
    """(index a, index b, t) to interpolate at weight w along the sorted
    weights, extrapolating past the ends with the end segments"""
    i = 0
    while i < len(weights) - 2 and w > weights[i + 1]:
        i += 1
    a, b = weights[i], weights[i + 1]
    return i, i + 1, (w - a) / (b - a)


def is_lower(g):
    """glyphs that live at x-height: scaled so x-height lands exactly"""
    name = g.name
    base = name.split('.')[0]
    if '_' in base:                                   # ligatures: f_f, f_b, brevecomb_acutecomb
        parts = base.split('_')
        return all(is_lower_name(p) for p in parts)
    return is_lower_name(base, g.unicode, '.case' in name)


def is_lower_name(base, uni=None, case=False):
    info = get_glyph(base)
    u = uni or info.unicode
    cat = unicodedata.category(chr(int(u, 16))) if u else ''
    if info.category == 'Mark':
        return not case
    if cat == 'Ll':
        return True
    if cat == 'Sk' and base in ('acute', 'grave', 'breve', 'caron', 'circumflex', 'dieresis', 'dotaccent',
                                'macron', 'ring', 'tilde', 'hungarumlaut', 'ogonek', 'cedilla'):
        return True
    if base in ('fi', 'fl', 'f_f', 'f_f_i', 'f_f_l'):
        return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--scale', type=float, default=1.2)
    ap.add_argument('--family', default='AA Bridge Slab Tall')
    a = ap.parse_args()
    S = a.scale

    font = glyphsLib.GSFont(a.src)
    masters = {m.id: m for m in font.masters}
    sizes = sorted({float(m.axes[1]) for m in font.masters})

    def layer_at(g):
        return {location(l, masters): l for l in g.layers if l.associatedMasterId in masters}

    weights = {o: sorted(w for (w, oo) in layer_at(font.glyphs['H']) if oo == o) for o in sizes}

    # horizontal stroke thickness along the weight axis, from the H bar, the
    # o and O hairlines and the n serif at Thin / Regular / Bold
    samples = {}
    for o in sizes:
        ws = weights[o]
        rows = []
        for name, x in (('H', None), ('o', None), ('O', None), ('n', 40)):
            L = layer_at(font.glyphs[name])
            runs = [vertical_runs(L[(w, o)], x if x is not None else L[(w, o)].width / 2) for w in ws]
            rows += zip(*runs)
        samples[o] = rows

    def piecewise(ws, vs, w):
        i, j, t = segment(ws, w)
        return vs[i] + (vs[j] - vs[i]) * t

    def ref_weight(w, o):
        """the weight whose horizontals are 1/S as thick as at weight w"""
        ws = weights[o]
        out = []
        for hs in samples[o]:
            h = piecewise(ws, hs, w) / S
            i = 0 if h <= hs[1] else len(ws) - 2
            (w0, h0), (w1, h1) = (ws[i], hs[i]), (ws[i + 1], hs[i + 1])
            out.append(w0 + (h - h0) / (h1 - h0) * (w1 - w0))
        return sum(out) / len(out)

    for o in sizes:
        for w in weights[o]:
            print(f'opsz {o:g} wght {w:g}: reference weight {ref_weight(w, o):.1f}')

    def sides(ws):
        """split a glyph's layer weights where two sit 1-2 units apart (a
        design switch, as in naira and won): never interpolate across one"""
        groups = [[ws[0]]]
        for w in ws[1:]:
            if w - groups[-1][-1] <= 2:
                groups.append([w])
            else:
                groups[-1].append(w)
        return groups

    def light_ys(g, loc_, snaps):
        """y of every node (and anchor) of glyph g interpolated at the
        reference weight for location loc_, along that glyph's own layers"""
        w, o = loc_
        ws = next(s for s in sides(sorted(ww for (ww, oo) in snaps if oo == o)) if w in s)
        if len(ws) == 1:                      # nothing to interpolate with
            return snaps[loc_]
        i, j, t = segment(ws, ref_weight(w, o))
        A, B = snaps[(ws[i], o)], snaps[(ws[j], o)]
        nodes = [[ya + (yb - ya) * t for ya, yb in zip(pa, pb)] for pa, pb in zip(A[0], B[0])]
        anchors = {k: A[1][k] + (B[1][k] - A[1][k]) * t for k in A[1] if k in B[1]}
        return nodes, anchors

    def snapshot(g):
        return {loc_: ([[n.position.y for n in p.nodes] for p in l.paths], {an.name: an.position.y for an in l.anchors})
                for loc_, l in layer_at(g).items()}

    # vertical scale per location: caps land on S x cap, lowercase on S x x-height
    scale = {}
    for name, key in (('H', 'cap'), ('x', 'low')):
        g = font.glyphs[name]
        snaps = snapshot(g)
        for loc_ in snaps:
            top = max(max(p) for p in snaps[loc_][0])
            light = max(max(p) for p in light_ys(g, loc_, snaps)[0])
            scale[(key, loc_)] = S * top / light

    counts = {'low': 0, 'cap': 0}
    worst_off = 0.0
    for g in font.glyphs:
        L = layer_at(g)
        snaps = snapshot(g)
        key = 'low' if is_lower(g) else 'cap'
        counts[key] += 1
        # read joins, real smooth nodes and the merged contour count off the
        # untouched drawings first
        prep = {loc_: (find_joins(l), [{i for i, ang in node_angles(p).items() if ang <= CORNER} for p in l.paths],
                       len(union(l.paths)))
                for loc_, l in L.items()}
        drawn = {loc_: [[(n.position.x, n.position.y) for n in p.nodes] for p in l.paths] for loc_, l in L.items()}
        for loc_, l in L.items():
            w, o = loc_
            ws = weights[o]
            s = piecewise(ws, [scale[(key, (ww, o))] for ww in ws], w)
            ys, anchors = light_ys(g, loc_, snaps)
            joins, smooth, want = prep[loc_]
            for p, py, keep in zip(l.paths, ys, smooth):
                for n, y in zip(p.nodes, py):
                    n.position.y = y * s
                realign_smooth(p, set(node_angles(p)) - keep)
                for n in p.nodes:
                    n.position.x, n.position.y = round(n.position.x), round(n.position.y)
            snap_joins(l, joins)
            if g.name in SPINES:
                r = fix_spine(l, drawn[loc_])
                if g.name in ('S', 's'):
                    print(f'  spine {g.name} {loc_}: drawn {r[0]:.1f}, tall {r[1]:.1f} -> {r[2]:.1f}')
            for i, k, before, after in repair_pinholes(l, want):
                print(f'  pinhole closed: {g.name} {loc_} path {i} node {k} {before} -> {after}')
            left = len(union(l.paths)) - want
            if left:
                print(f'  STILL DIFFERENT: {g.name} {loc_} merged contours {want} -> {want + left}')
            for an in l.anchors:
                if an.name in anchors:
                    an.position.y = round(anchors[an.name] * s)
    print(f'glyphs scaled to x-height: {counts["low"]}, to cap height: {counts["cap"]}')

    # metrics, zones, line spacing, names
    for m in font.masters:
        old = (m.xHeight, m.capHeight, m.ascender, m.descender)
        m.xHeight, m.capHeight = round(S * m.xHeight), round(S * m.capHeight)
        m.ascender, m.descender = round(S * m.ascender), round(S * m.descender)
        for z in m.alignmentZones:
            z.position, z.size = round(S * z.position), round(S * z.size)
        for p in m.customParameters:
            if p.name in LINE_PARAMS:
                p.value = round(S * p.value)
        print(f'{m.name:10} x/cap/asc/desc {old} -> {(m.xHeight, m.capHeight, m.ascender, m.descender)}')
    for p in font.customParameters:
        if p.name == 'Family Alignment Zones':
            zs = []
            for z in p.value:
                pos, size = (int(v) for v in z.strip('{}').split(','))
                zs.append(f'{{{round(S * pos)}, {round(S * size)}}}')
            p.value = zs
    old_family = font.familyName
    font.familyName = a.family
    for inst in font.instances:
        for p in inst.customParameters:
            if p.name == 'familyName' and p.value.startswith(old_family):
                p.value = a.family + p.value[len(old_family):]
    font.save(a.out)


if __name__ == '__main__':
    main()
