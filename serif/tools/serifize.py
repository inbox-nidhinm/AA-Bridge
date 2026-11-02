"""Make AA Bridge Serif (bracketed) or AA Bridge Serif Wedge from AA Bridge Slab's source.

usage: serifize.py SRC.glyphs OUT.glyphs [--style bracketed|wedge] [--family NAME]

--style wedge swaps the bracketed serif for a pointed wedge: a concave line from
the stem straight down to a sharp tip on the baseline (no flat, no thickness),
angled wedges for lowercase head serifs, and beaks and spurs that end in a
near point with a straighter, more triangular inner edge. Everything else below
is shared, including the unchanged reach (so spacing and kerning match the Slab).

1. Slabs. A slab in AA Bridge Slab is a run drawn into a stem contour:
   baseline -> Cbase (outer bottom corner) -> Ctop (outer top corner) -> P (where
   the slab's top meets the stem) -> stem. Each run is replaced by a bracketed
   serif: half the slab's thickness, the same reach, a flat end, and a long
   concave bracket that meets the stem higher up. Lowercase head serifs (top of
   n, i, u, k, ... when the top line runs off to a shoulder, not to another
   serif) get an angled top. The same runs are replaced in every layer, so
   masters stay compatible. Reach is unchanged, so spacing and kerning are too.
2. Brackets. The Slab's small fillet contours that sit on a replaced slab are
   deleted (the new serif carries its own bracket). Others stay.
3. Beaks on arms (T E F L Z z 7 2 ..., contours llllooc / lloocll): the tip is
   narrowed to the new serif's thickness and the inner edge becomes one long
   concave bracket into the arm.
4. Spurs (S C G s and currency, contours lllll listed in SPURS and any contour of
   the same shape elsewhere): the tip is narrowed to the same thickness, so the
   spur tapers out of the stroke instead of widening.
"""
import argparse
import math
from collections import defaultdict

import glyphsLib
from glyphsLib.classes import GSNode
from glyphsLib.types import Point

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--style', choices=['bracketed', 'wedge'], default='bracketed')
ap.add_argument('--family', default=None)
args = ap.parse_args()
if args.family is None:
    args.family = {'bracketed': 'AA Bridge Serif', 'wedge': 'AA Bridge Serif Wedge'}[args.style]

# serif proportions, in units of the slab's own thickness t0 / reach L0
T_RATIO = 0.5        # serif thickness
BRACKET = 1.3        # how far up the stem the bracket climbs, beyond the serif
U1 = 0.42            # where the flat top of the serif turns into the bracket
F_BR = 0.6           # bracket handle length
HEAD_DROP = 0.6      # angled head serif: tip sits this far below the top line
BEAK_T = 0.55        # beak / spur tip width
F_BEAK = 0.62
F_SPUR = 0.7

# wedge, in the same units
W_H = 1.9            # wedge climbs this far up the stem (foot)
W_CONC = 0.22        # how much the wedge's edge bows in toward the corner
W_DROP = 0.85        # head wedge: tip sits this far below the top line
W_HEAD_H = 1.5       # head wedge: climbs this far up the stem beyond the tip
W_H_BOLD = 1.2       # heavier slabs get relatively shorter wedges, so counters stay open:
W_HEAD_H_BOLD = 1.05 #   the factor slides from the Thin value (slab 16) to this (slab 94)
W_SLANT = 0.6        # and wedges on slanted stems are shorter by 1 / (1 + W_SLANT * slant)
if args.style == 'wedge':
    BEAK_T = 0.14    # beaks and spurs end in a near point
    F_BEAK = 0.3     # and their inner edge is almost straight
    F_SPUR = 0.35

# wedge, second pass (2026-11-01): smaller wedges, the same on both sides of a stem,
# straight-sided beaks and spurs square to the grid, and G J R redrawn without slab traits
W_REACH = 0.8        # foot/head wedge reach: this share of H's slab reach, and never more
                     #   than the shorter of the two slabs on that stem (so both sides match)
W_ASPECT = 0.8       # wedge height = this share of its reach (Harvey ~0.73, Geist ~0.9)
W_HDROP = 0.45       # lowercase head wedge: tip sits this share of the reach below the top line
W_CONC2 = 0.12       # how much the wedge edge bows in (was W_CONC)
WB_TIP = 0.2         # beak/spur tip: a flat this share of the slab thickness, parallel to the arm
WB_IN = 0.6          # beak inner edge lands on the arm this share of the beak's length in
WB_CONC = 0.12       # beak inner edge bows in this much
WS_BASE = 1.0        # spur base: inner edge meets the bowl this many slab thicknesses in
                     #   from the (now vertical) outer edge, so C G S get a thick base
WS_SLOPE = 1.0       # a downward spur's inner edge rises this steeply into the curve
WG_BEAK = 0.55       # G bar's left beak: drops this share of the bar thickness below the bar

SPURS = {'C': [1], 'G': [3], 'S': [1, 2], 's': [1, 2], 'cedi': [2],
         'colonsign': [3], 'dollar': [2, 3], 'euro': [3], 'guarani': [4],
         'lira': [5], 'sterling': [3], 'section': [1, 3], 'copyright': [1]}

f = glyphsLib.GSFont(args.src)
master_by_id = {m.id: m for m in f.masters}


def sig(p):
    return ''.join('o' if n.type == 'offcurve' else n.type[0] for n in p.nodes)


def layers(g):
    return [l for l in g.layers if l.paths]


# ---------- contour <-> on-curve list -------------------------------------

def to_pts(path):
    """[(pos, type, offs, smooth)] where type/offs describe the segment INTO pos"""
    nodes = list(path.nodes)
    while nodes[-1].type == 'offcurve':
        nodes = nodes[-1:] + nodes[:-1]
    out, offs = [], []
    for n in nodes:
        if n.type == 'offcurve':
            offs.append((n.position.x, n.position.y))
        else:
            out.append([(n.position.x, n.position.y), n.type, offs, n.smooth])
            offs = []
    return out


def from_pts(pts):
    nodes = []
    for pos, typ, offs, smooth in pts:
        for o in offs:
            nodes.append(GSNode((round(o[0]), round(o[1])), 'offcurve'))
        n = GSNode((round(pos[0]), round(pos[1])), typ)
        n.smooth = smooth
        nodes.append(n)
    return nodes


def reverse_pts(pts):
    n = len(pts)
    out = []
    for i in range(n - 1, -1, -1):
        nxt = pts[(i + 1) % n]
        out.append([pts[i][0], nxt[1], list(reversed(nxt[2])), pts[i][3]])
    return out


# ---------- slab sites ------------------------------------------------------

def find_sites(pts):
    """forward-orientation sites: indices c such that pts[c]=Cbase, c+1=Ctop, c+2=P"""
    n = len(pts)
    sites = []
    for c in range(n):
        prv, cb, ct, P, nx = (pts[(c + j) % n] for j in (-1, 0, 1, 2, 3))
        if not (cb[1] == 'line' and ct[1] == 'line' and P[1] == 'line'):
            continue
        (x0, y0), (x1, y1), (px, py) = cb[0], ct[0], P[0]
        if x0 != x1 or not (8 <= abs(y1 - y0) <= 120):
            continue
        if py != y1 or not (8 <= abs(px - x1) <= 240):
            continue
        if prv[0][1] != y0 or prv[0][0] == x0:
            continue
        sx = 1 if x0 > px else -1
        sy = 1 if y1 > y0 else -1
        if (prv[0][0] - x0) * sx >= 0:       # baseline must come from inside
            continue
        if nx[1] != 'line':                  # stems are straight
            continue
        (qx, qy) = nx[0]
        if (qy - py) * sy <= abs(y1 - y0):   # stem runs on into the letter
            continue
        dxdy = (qx - px) / (qy - py)
        if abs(dxdy) > 1.2:
            continue
        X0 = px + dxdy * (y0 - py)
        # on a steep diagonal the stem's line can pass the slab's end: L0 < 0
        sites.append(dict(c=c, Y0=y0, X0=X0, sx=sx, sy=sy, k=sx * sy * dxdy,
                          L0=(x0 - X0) * sx, t0=abs(y1 - y0), run=abs(qy - py),
                          prev=prv[0], P=(px, py)))
    return sites


def wedge_profile(s, head):
    """sharp tip on the line, one concave curve up to the stem"""
    k = s['k']
    L = s['Lw']                              # reach, the same on both sides of the stem
    d = W_HDROP * L if head else 0
    h = d + W_ASPECT * L / (1 + W_SLANT * abs(k))
    h = min(h, s['run'] * 0.8 + s['t0'])
    tip = (L, d)
    S = (k * h, h)
    corner = (k * d, d)
    m1 = (tip[0] + (S[0] - tip[0]) / 3, tip[1] + (S[1] - tip[1]) / 3)
    m2 = (tip[0] + (S[0] - tip[0]) * 2 / 3, tip[1] + (S[1] - tip[1]) * 2 / 3)
    c1 = (m1[0] + W_CONC2 * (corner[0] - m1[0]), m1[1] + W_CONC2 * (corner[1] - m1[1]))
    c2 = (m2[0] + W_CONC2 * (corner[0] - m2[0]), m2[1] + W_CONC2 * (corner[1] - m2[1]))
    return [(tip, 'line', []), (S, 'curve', [c1, c2])]


def profile(s, head):
    """local points from Cbase' to S' : [(pos, type, offs)]"""
    if args.style == 'wedge':
        return wedge_profile(s, head)
    L0, t0, k = s['L0'], s['t0'], s['k']
    T = T_RATIO * t0
    d = HEAD_DROP * t0 if head else 0
    h = d + T + BRACKET * t0
    h = min(h, s['run'] * 0.8 + t0)          # stay below the stem's next node
    L = L0
    u1 = k * (d + T) + U1 * (L - k * (d + T))
    p0 = (u1, d + T)
    S = (k * h, h)
    c1 = (p0[0] - F_BR * (p0[0] - k * p0[1]), p0[1])
    v2 = h - F_BR * (h - p0[1])
    c2 = (k * v2, v2)
    return [((L, d), 'line', []), ((L, d + T), 'line', []), (p0, 'line', []), (S, 'curve', [c1, c2])]


def apply_sites(pts, sites, is_head):
    n = len(pts)
    by_c = {s['c']: s for s in sites}
    drop = set()
    for s in sites:
        drop |= {(s['c'] + 1) % n, (s['c'] + 2) % n}
    out = []
    for i in range(n):
        if i in drop:
            continue
        if i in by_c:
            s = by_c[i]
            g = lambda p, s=s: (s['X0'] + s['sx'] * p[0], s['Y0'] + s['sy'] * p[1])
            prof = profile(s, is_head(s))
            typ0 = pts[i][1]
            offs0 = pts[i][2]
            for j, (p, typ, offs) in enumerate(prof):
                if j == 0:
                    out.append([g(p), typ0, offs0, False])
                else:
                    out.append([g(p), typ, [g(o) for o in offs], j == len(prof) - 1])
        else:
            out.append(pts[i])
    return out


# ---------- per layer --------------------------------------------------------

def layer_sites(l):
    """{(path, orient, c): site} for one layer"""
    res = {}
    for pi, p in enumerate(l.paths):
        pts = to_pts(p)
        for s in find_sites(pts):
            res[(pi, 'f', s['c'])] = s
        for s in find_sites(reverse_pts(pts)):
            res[(pi, 'r', s['c'])] = s
    return res


def cap_of(l):
    m = master_by_id.get(l.associatedMasterId)
    return m.capHeight if m else 700


report = defaultdict(int)
partial = []


def bbox(p):
    xs = [n.position.x for n in p.nodes]; ys = [n.position.y for n in p.nodes]
    return min(xs), min(ys), max(xs), max(ys)


def near(b, pt, r):
    return b[0] - r <= pt[0] <= b[2] + r and b[1] - r <= pt[1] <= b[3] + r


Lref_by_layer = {}


def lref_of(l):
    """H's mean slab reach in this layer: the yardstick for every wedge's reach"""
    if l.name not in Lref_by_layer:
        h = next((x for x in layers(f.glyphs['H']) if x.name == l.name), None)
        if h is None:             # a one-off layer: use its master's value (measured up front)
            return Lref_by_layer[master_by_id[l.associatedMasterId].name]
        L = [s['L0'] for s in layer_sites(h).values()]
        Lref_by_layer[l.name] = sum(L) / len(L)
    return Lref_by_layer[l.name]


def set_wedge_reach(l, sites, common):
    """every wedge gets W_REACH of H's reach, but never more than either slab on its
    stem, so the two wedges of one stem always match"""
    ref = W_REACH * lref_of(l)
    for key in common:
        s = sites[key]
        if s['L0'] <= 0:              # steep diagonal: the stem's own line passes the tip
            s['Lw'] = s['L0']
            continue
        best = None
        for k2 in common:
            o = sites[k2]
            if k2[0] != key[0] or o['Y0'] != s['Y0'] or o['sy'] != s['sy'] or o['sx'] != -s['sx']:
                continue
            gap = (o['X0'] - s['X0']) * -s['sx']
            if 0 < gap < 400 and o['L0'] > 0 and (best is None or gap < best[0]):
                best = (gap, o)
        Lw = min(ref, s['L0'])
        if best:
            Lw = min(Lw, best[1]['L0'])
        s['Lw'] = Lw


def convert_slabs(g):
    ls = layers(g)
    if not ls:
        return
    per = [layer_sites(l) for l in ls]
    common = set.intersection(*[set(p) for p in per])
    if any(set(p) - common for p in per):
        partial.append(g.name)
    if not common:
        return
    # brackets on replaced slabs: decide on all layers, delete everywhere
    gone = set()
    for l, sites in zip(ls, per):
        for pi, p in enumerate(l.paths):
            if sig(p) not in ('llloocl', 'looclll'):
                continue
            b = bbox(p)
            for key in common:
                s = sites[key]
                if key[0] != pi and near(b, s['P'], 6):
                    gone.add(pi)
    for l, sites in zip(ls, per):
        cap = cap_of(l)
        cbases = {(round(sites[k]['X0'] + sites[k]['sx'] * sites[k]['L0']), sites[k]['Y0']) for k in common}

        def is_head(s):
            if s['sy'] != -1 or abs(s['Y0'] - cap) < 2:
                return False
            return (round(s['prev'][0]), s['prev'][1]) not in cbases

        if args.style == 'wedge':
            set_wedge_reach(l, sites, common)

        for pi in {k[0] for k in common}:
            p = l.paths[pi]
            pts = to_pts(p)
            fw = [sites[k] for k in common if k[0] == pi and k[1] == 'f']
            rv = [sites[k] for k in common if k[0] == pi and k[1] == 'r']
            if rv:
                rp = reverse_pts(pts)
                pts = reverse_pts(apply_sites(rp, rv, is_head))
                # forward indices moved: find them again on the new contour
                if fw:
                    want = {(s['Y0'], round(s['X0'])): s for s in fw}
                    fw = [s for s in find_sites(pts) if (s['Y0'], round(s['X0'])) in want]
                    for s in fw:
                        if 'Lw' in want[(s['Y0'], round(s['X0']))]:
                            s['Lw'] = want[(s['Y0'], round(s['X0']))]['Lw']
            if fw:
                pts = apply_sites(pts, fw, is_head)
            p.nodes = from_pts(pts)
        for pi in sorted(gone, reverse=True):
            del l.paths[pi]
    report['slabs'] += len(common)
    report['brackets'] += len(gone)
    report['glyphs'] += 1


# ---------- beaks ------------------------------------------------------------

t0_by_layer = {}
for l in layers(f.glyphs['H']):
    pts = to_pts(l.paths[0])
    t0_by_layer[l.name] = abs(pts[1][0][1] - pts[0][0][1])
t0_by_master = {master_by_id[l.layerId].id: t0_by_layer[l.name] for l in layers(f.glyphs['H']) if l.layerId in master_by_id}


def t0_of(l):
    return t0_by_layer.get(l.name) or t0_by_master[l.associatedMasterId]


def line_x(a, b, c, d):
    """intersection of line ab with line cd"""
    x1, y1 = a; x2, y2 = b; x3, y3 = c; x4, y4 = d
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def unit(v):
    d = math.hypot(v[0], v[1]) or 1.0
    return (v[0] / d, v[1] / d)


def beak_side(p):
    """(M is the curve's end node?, how clear that is): see redo_beak_wedge"""
    pts = to_pts(p)
    n = len(pts)
    ci = next(i for i, q in enumerate(pts) if q[1] == 'curve')
    A, B = pts[(ci - 1) % n][0], pts[ci][0]
    eb, ea = math.dist(B, pts[(ci + 1) % n][0]), math.dist(A, pts[(ci - 2) % n][0])
    return eb >= ea, abs(eb - ea) / max(eb, ea, 1)


def redo_beak_wedge(l, p, side=None):
    """wedge beak: outer edge square to the arm, a small flat tip parallel to the arm,
    and a near-straight inner edge back up to the arm.

    The Slab beak is K -curve-> M -> AO -> O -> I -> K (or the reverse): M and AO lie
    on the arm, O-I is the tip. M is the curve end whose other edge runs along the
    arm (the long one); the tip is then always two edges on from M. (Picking the
    shorter edge as the tip, as the bracketed version does, fails on wide heavy
    beaks such as Bold 5 and 2, which then break off.)"""
    pts = to_pts(p)
    if len(pts) != 5 or sum(1 for q in pts if q[1] == 'curve') != 1:
        return False
    n = 5
    ci = next(i for i, q in enumerate(pts) if q[1] == 'curve')
    A, B = pts[(ci - 1) % n][0], pts[ci][0]
    if side is None:
        side = beak_side(p)[0]
    if side:
        M_is_B = True
        M, AO, O, I = B, pts[(ci + 1) % n][0], pts[(ci + 2) % n][0], pts[(ci + 3) % n][0]
    else:
        M_is_B = False
        M, AO, O, I = A, pts[(ci - 2) % n][0], pts[(ci - 3) % n][0], pts[(ci - 4) % n][0]
    t0 = t0_of(l)
    u = unit((AO[0] - M[0], AO[1] - M[1]))            # along the arm, outwards
    v = (O[0] - AO[0], O[1] - AO[1])
    along = v[0] * u[0] + v[1] * u[1]
    nv = unit((v[0] - along * u[0], v[1] - along * u[1]))   # square to the arm, toward the tip
    hb = v[0] * nv[0] + v[1] * nv[1]                  # beak length
    O2 = (AO[0] + hb * nv[0], AO[1] + hb * nv[1])
    tb = WB_TIP * t0
    I2 = (O2[0] - tb * u[0], O2[1] - tb * u[1])
    Lb = min(math.dist(M, AO), tb + WB_IN * hb)
    Mi = (AO[0] - Lb * u[0], AO[1] - Lb * u[1])
    Kc = (AO[0] - tb * u[0], AO[1] - tb * u[1])      # the inside corner the edge bows toward
    m1 = (I2[0] + (Mi[0] - I2[0]) / 3, I2[1] + (Mi[1] - I2[1]) / 3)
    m2 = (I2[0] + (Mi[0] - I2[0]) * 2 / 3, I2[1] + (Mi[1] - I2[1]) * 2 / 3)
    c1 = (m1[0] + WB_CONC * (Kc[0] - m1[0]), m1[1] + WB_CONC * (Kc[1] - m1[1]))
    c2 = (m2[0] + WB_CONC * (Kc[0] - m2[0]), m2[1] + WB_CONC * (Kc[1] - m2[1]))
    # tuck the beak's top edge a few units into the arm: an edge that only touches the
    # arm can open into a hairline gap at in-between weights (₇ at 16pt Light did)
    ov = 3
    AO = (AO[0] - ov * nv[0], AO[1] - ov * nv[1])
    Mi = (Mi[0] - ov * nv[0], Mi[1] - ov * nv[1])
    if M_is_B:     # I -> K -curve-> M -> AO -> O : keep that direction
        new = [[Mi, 'curve', [c1, c2], False], [AO, 'line', [], False],
               [O2, 'line', [], False], [I2, 'line', [], False]]
    else:          # O -> AO -> M -curve-> K -> I
        new = [[O2, 'line', [], False], [AO, 'line', [], False],
               [Mi, 'line', [], False], [I2, 'curve', [c2, c1], False]]
    p.nodes = from_pts(new)
    return True


def redo_beak(l, p):
    if args.style == 'wedge':
        return redo_beak_wedge(l, p)
    pts = to_pts(p)
    if len(pts) != 5 or sum(1 for q in pts if q[1] == 'curve') != 1:
        return False
    ci = next(i for i, q in enumerate(pts) if q[1] == 'curve')
    # rotate so the curve is the segment into pts[0]:  X=pts[4] -> Y=pts[0]
    pts = pts[ci:] + pts[:ci]
    X, Y, Z1, Z2, Z3 = pts[4][0], pts[0][0], pts[1][0], pts[2][0], pts[3][0]
    d12 = math.dist(Z1, Z2); d23 = math.dist(Z2, Z3)
    tb = BEAK_T * t0_of(l)
    if d12 < d23:
        # Y=M, Z1=I, Z2=O, Z3=AO, X=AI  :  AI -curve-> M -line-> I -> O -> AO -> AI
        I, O, AO, AI = Z1, Z2, Z3, X
        w = min(1.0, tb / d12)
        I2 = (O[0] + (I[0] - O[0]) * w, O[1] + (I[1] - O[1]) * w)
        K = line_x(AO, AI, I2, (I2[0] + AO[0] - O[0], I2[1] + AO[1] - O[1])) or I2
        c1 = (AI[0] + F_BEAK * (K[0] - AI[0]), AI[1] + F_BEAK * (K[1] - AI[1]))
        c2 = (I2[0] + F_BEAK * (K[0] - I2[0]), I2[1] + F_BEAK * (K[1] - I2[1]))
        new = [[I2, 'curve', [c1, c2], False], [O, 'line', [], False],
               [AO, 'line', [], False], [AI, 'line', [], False]]
    else:
        # X=M, Z3=I, Z2=O, Z1=AO, Y=AI  :  M -curve-> AI -> AO -> O -> I -line-> M
        AI, AO, O, I = Y, Z1, Z2, Z3
        w = min(1.0, tb / d23)
        I2 = (O[0] + (I[0] - O[0]) * w, O[1] + (I[1] - O[1]) * w)
        K = line_x(AO, AI, I2, (I2[0] + AO[0] - O[0], I2[1] + AO[1] - O[1])) or I2
        c1 = (I2[0] + F_BEAK * (K[0] - I2[0]), I2[1] + F_BEAK * (K[1] - I2[1]))
        c2 = (AI[0] + F_BEAK * (K[0] - AI[0]), AI[1] + F_BEAK * (K[1] - AI[1]))
        new = [[AI, 'curve', [c1, c2], False], [AO, 'line', [], False],
               [O, 'line', [], False], [I2, 'line', [], False]]
    p.nodes = from_pts(new)
    return True


def shape(p):
    q = [(n.position.x, n.position.y) for n in p.nodes]
    return (sig(p), tuple((x - q[0][0], y - q[0][1]) for x, y in q))


spur_shapes = defaultdict(set)
for name, idxs in SPURS.items():
    for l in layers(f.glyphs[name]):
        for i in idxs:
            spur_shapes[l.name].add(shape(l.paths[i]))


def flatten(path, steps=16):
    """closed polyline of a contour (cubic segments sampled)"""
    nodes = list(path.nodes)
    while nodes[-1].type == 'offcurve':
        nodes = nodes[-1:] + nodes[:-1]
    cur = (nodes[-1].position.x, nodes[-1].position.y)
    out, offs = [], []
    for nd in nodes:
        q = (nd.position.x, nd.position.y)
        if nd.type == 'offcurve':
            offs.append(q)
            continue
        if nd.type == 'curve' and len(offs) == 2:
            a, b = offs
            for i in range(1, steps + 1):
                t = i / steps; mt = 1 - t
                out.append((mt**3 * cur[0] + 3 * mt * mt * t * a[0] + 3 * mt * t * t * b[0] + t**3 * q[0],
                            mt**3 * cur[1] + 3 * mt * mt * t * a[1] + 3 * mt * t * t * b[1] + t**3 * q[1]))
        else:
            out.append(q)
        offs = []
        cur = q
    return out


def crossings_x(l, x, skip):
    """y values where the layer's other contours cross the vertical line at x"""
    ys = []
    for p in l.paths:
        if p is skip or sig(p) in ('looclll', 'llloocl'):    # itself, or a bracket piece
            continue
        poly = flatten(p)
        for a, b in zip(poly, poly[1:] + poly[:1]):
            if (a[0] - x) * (b[0] - x) < 0 or (a[0] == x and b[0] != x):
                t = (x - a[0]) / (b[0] - a[0])
                ys.append(a[1] + t * (b[1] - a[1]))
    return ys


def narrow_spur_wedge(l, p, cx):
    """wedge spur (C G S s $ ...): the outer edge stands vertical, the tip is a small
    flat, and the inner edge runs straight down to meet the bowl WS_BASE slab
    thicknesses in from the outer edge, so the spur has a thick base on its inner
    side. Returns J, the node where the old spur met the stroke."""
    pts = to_pts(p)
    n = len(pts)
    best = None
    for i in range(n):
        a, b = pts[i][0], pts[(i + 1) % n][0]
        if a[1] == b[1] and (best is None or abs(b[0] - a[0]) > best[0]):
            best = (abs(b[0] - a[0]), i, (i + 1) % n)
    if not best:
        return False
    _, i, j = best
    a, b = pts[i][0], pts[j][0]
    inner, outer = (i, j) if abs(a[0] - cx) < abs(b[0] - cx) else (j, i)
    t0 = t0_of(l)
    o = pts[outer][0]
    bo = (outer + (1 if (outer - inner) % n == 1 else -1)) % n      # outer edge's other end
    base = pts[bo][0]
    o2 = (base[0], o[1])                                           # vertical outer edge
    sgn = 1 if pts[inner][0][0] > o[0] else -1
    I2 = (o2[0] + sgn * WB_TIP * t0, o[1])
    pts[outer][0] = o2
    pts[inner][0] = I2
    step = 1 if (inner - outer) % n == 1 else -1
    jn = (inner + step) % n
    J = pts[jn][0]
    # X: where the new inner edge meets the bowl, WS_BASE * t0 in from the outer edge
    xt = o2[0] + sgn * WS_BASE * t0
    up = o[1] > base[1]                                            # tip on top?
    ys = [y for y in crossings_x(l, xt, p) if (y < o[1] if up else y > o[1])]
    if ys:
        yc = max(ys) if up else min(ys)
        X = (xt, yc - 0.15 * t0 if up else yc + 0.15 * t0)        # just inside the stroke
    else:
        X = ((I2[0] + J[0]) / 2, (I2[1] + J[1]) / 2)
    if not up:
        # a spur hanging from a terminal (S s $ § lower left) stops short of the
        # baseline: a beak whose inner edge rises at WS_SLOPE into the curve, as in
        # Harvey and Geist, not a spike down to the line beside a white wedge
        yt = max(o[1], X[1] - WS_SLOPE * abs(X[0] - I2[0]))
        o2, I2 = (o2[0], yt), (I2[0], yt)
        pts[outer][0], pts[inner][0] = o2, I2
    pts[jn][1], pts[jn][2] = 'line', []
    xnode = [X, 'line', [], False]
    if step == 1:
        pts.insert(inner + 1, xnode)
    else:
        pts[inner][1], pts[inner][2] = 'line', []
        pts.insert(inner, xnode)
    p.nodes = from_pts(pts)
    return J


def narrow_spur(l, p, cx):
    """thin tip, and the inner edge becomes a bracket sweeping up into the stroke"""
    if args.style == 'wedge':
        return narrow_spur_wedge(l, p, cx)
    pts = to_pts(p)
    n = len(pts)
    # tip: the longest horizontal edge
    best = None
    for i in range(n):
        a, b = pts[i][0], pts[(i + 1) % n][0]
        if a[1] == b[1] and (best is None or abs(b[0] - a[0]) > best[0]):
            best = (abs(b[0] - a[0]), i, (i + 1) % n)
    if not best:
        return False
    _, i, j = best
    a, b = pts[i][0], pts[j][0]
    inner, outer = (i, j) if abs(a[0] - cx) < abs(b[0] - cx) else (j, i)
    tb = BEAK_T * t0_of(l)
    o, q = pts[outer][0], pts[inner][0]
    w = min(1.0, tb / abs(q[0] - o[0]))
    I2 = (o[0] + (q[0] - o[0]) * w, q[1])
    pts[inner][0] = I2
    # J: the inner corner's other neighbour, where the spur meets the stroke
    step = 1 if (inner - outer) % n == 1 else -1
    jn = (inner + step) % n
    J = pts[jn][0]
    K = (I2[0], J[1])
    a = (I2[0] + F_SPUR * (K[0] - I2[0]), I2[1] + F_SPUR * (K[1] - I2[1]))
    b = (J[0] + F_SPUR * (K[0] - J[0]), J[1] + F_SPUR * (K[1] - J[1]))
    if step == 1:          # segment inner -> J is J's incoming one
        pts[jn][1], pts[jn][2] = 'curve', [a, b]
    else:                  # segment J -> inner is inner's incoming one
        pts[inner][1], pts[inner][2] = 'curve', [b, a]
    p.nodes = from_pts(pts)
    return J


def convert_beaks(g):
    ls = layers(g)
    if not ls:
        return
    npaths = len(ls[0].paths)
    spur_fillets = set()
    spur_paths = set()
    for pi in range(npaths):
        sigs = {sig(l.paths[pi]) for l in ls if pi < len(l.paths)}
        if len(sigs) != 1:
            continue
        s = sigs.pop()
        if s in ('llllooc', 'lloocll'):
            if args.style == 'wedge':
                # one reading for every layer, from the layer where it is clearest
                side = max((beak_side(l.paths[pi]) for l in ls), key=lambda x: x[1])[0]
                for l in ls:
                    redo_beak_wedge(l, l.paths[pi], side)
            else:
                for l in ls:
                    redo_beak(l, l.paths[pi])
            report['beaks'] += 1
        elif s == 'lllll' and all(shape(l.paths[pi]) in spur_shapes.get(l.name, ()) for l in ls):
            for l in ls:
                J = narrow_spur(l, l.paths[pi], l.width / 2)
                # the Slab's fillet for this spur goes: the new inner edge is the bracket
                r = t0_of(l)
                for qi, q in enumerate(l.paths):
                    if sig(q) == 'looclll' and near(bbox(q), J, r):
                        spur_fillets.add(qi)
            report['spurs'] += 1
            spur_paths.add(pi)
    if args.style == 'wedge':
        # a reshaped spur can look like a bracket piece; it must not delete itself
        spur_fillets -= spur_paths
    for pi in sorted(spur_fillets, reverse=True):
        for l in ls:
            del l.paths[pi]
    report['spur fillets'] += len(spur_fillets)


# ---------- wedge: G J R redrawn without slab traits ------------------------------
# These run on the Slab outlines before the generic passes. J and R are left in slab
# form (top slabs on J, slab feet on the new R leg) so the generic pass wedges them
# exactly like every other stem; G is drawn in its final wedge form. Accented letters
# are decomposed in the source, so each change is planned on the base letter and then
# swapped into every glyph holding the same contours (matched by shape, 2-unit
# tolerance, any offset: Ǉ and Ǌ carry a shifted J).

def shape_of(p):
    return sig(p), [(nd.position.x, nd.position.y) for nd in p.nodes]


def offset_match(p, ref):
    s, q = shape_of(p)
    rs, rq = ref
    if s != rs or len(q) != len(rq):
        return None
    dx, dy = q[0][0] - rq[0][0], q[0][1] - rq[0][1]
    if all(abs(a[0] - b[0] - dx) <= 2 and abs(a[1] - b[1] - dy) <= 2 for a, b in zip(q, rq)):
        return (dx, dy)
    return None


def moved(pts, d):
    return [[(q[0][0] + d[0], q[0][1] + d[1]), q[1], [(o[0] + d[0], o[1] + d[1]) for o in q[2]], q[3]]
            for q in pts]


def redraw(base, idxs, build):
    """replace contours idxs of `base` (and their copies everywhere) with build(layer),
    a list as long as idxs of new on-curve lists (None deletes that contour)"""
    plan = {}
    for l in layers(f.glyphs[base]):
        plan[l.name] = ([shape_of(l.paths[i]) for i in idxs], build(l))
    done, where_all = [], []
    for g in f.glyphs:
        ls = layers(g)
        if not ls or any(l.name not in plan for l in ls):
            continue
        hits = {}
        for l in ls:
            refs, news = plan[l.name]
            for pi, p in enumerate(l.paths):
                d = offset_match(p, refs[0])
                if d is None:
                    continue
                rest = []
                for r in refs[1:]:
                    pj = next((j for j, p2 in enumerate(l.paths)
                               if (lambda e: e is not None and abs(e[0] - d[0]) <= 2 and abs(e[1] - d[1]) <= 2)(offset_match(p2, r))), None)
                    rest.append(pj)
                # a contour that is only being deleted (a bracket) may be missing (₲)
                if all(pj is not None or nw is None for pj, nw in zip(rest, news[1:])):
                    hits[l.name] = ([pi] + rest, d)
                    break
        if not hits:
            continue
        if len(hits) != len(ls):
            print(f'  {base} redraw: {g.name} matches in only some layers, left alone')
            continue
        for l in ls:
            where, d = hits[l.name]
            for pi, new in zip(where, plan[l.name][1]):
                if new is not None:
                    l.paths[pi].nodes = from_pts(moved(new, d))
            for pi in sorted((pi for pi, new in zip(where, plan[l.name][1])
                              if new is None and pi is not None), reverse=True):
                del l.paths[pi]
            where_all.append((g, l, where, (round(d[0]), round(d[1]))))
        done.append(g.name)
    report['redrawn ' + base] = len(done)
    return where_all


def P(nd):
    return (nd.position.x, nd.position.y)


def conc_ctrl(a, b, corner, c):
    """handles for a gently concave edge a -> b that bows toward `corner`"""
    m1 = (a[0] + (b[0] - a[0]) / 3, a[1] + (b[1] - a[1]) / 3)
    m2 = (a[0] + (b[0] - a[0]) * 2 / 3, a[1] + (b[1] - a[1]) * 2 / 3)
    return [(m1[0] + c * (corner[0] - m1[0]), m1[1] + c * (corner[1] - m1[1])),
            (m2[0] + c * (corner[0] - m2[0]), m2[1] + c * (corner[1] - m2[1]))]


def build_G(l):
    """G: the bar ends in wedges (a beak dropping off its left end, a head wedge on the
    stem's right instead of the slab overhang) and the stem foot becomes a pointed
    spur cut diagonally from the bowl down to the baseline, as in Harvey and Geist.
    Contours: [1] stem lllll, [2] bar llll, [4] stem/bar bracket, [5] stem/bowl bracket."""
    st, bar = l.paths[1].nodes, l.paths[2].nodes
    s0, s1, s2, s3, s4 = (P(n) for n in st)           # BR, TR, chamfer, chamfer, BL
    b0, b1, b2, b3 = (P(n) for n in bar)               # BR, TR, TL, BL
    xs_r, xs_l, yb, yt, xl, xr = s0[0], s4[0], b0[1], b1[1], b2[0], b0[0]
    tbar = yt - yb
    t0 = t0_of(l)
    tb = WB_TIP * t0
    # right: a head wedge on the stem, its top on the bar's top line
    Lw = min(W_REACH * lref_of(l), xr - xs_r)
    h = min(W_ASPECT * Lw, 0.9 * tbar)
    q1, tip = (xs_r, yt - h), (xs_r + Lw, yt)
    # left: a beak dropping off the bar's end, outer edge vertical, small flat tip
    bd = WG_BEAK * tbar
    q4, q5 = (xl, yb - bd), (xl + tb, yb - bd)
    q6 = (xl + tb + 1.2 * bd, yb)
    new_bar = [[(xs_r, yb), 'line', [], False], [q1, 'line', [], False],
               [tip, 'curve', conc_ctrl(q1, tip, (xs_r, yt), W_CONC2), False],
               [(xl, yt), 'line', [], False], [q4, 'line', [], False], [q5, 'line', [], False],
               [q6, 'curve', conc_ctrl(q5, q6, (xl + tb, yb), WB_CONC), False]]
    # stem: cut from where the bowl meets it down to a small flat tip at the bottom right
    ys = [y for y in crossings_x(l, xs_l + 1, l.paths[1]) if 0 < y < s3[1]]
    hs = (min(ys) + 0.1 * t0) if ys else 0.5 * s3[1]
    new_stem = [[s0, 'line', [], False], [s1, 'line', [], False], [s2, 'line', [], False],
                [s3, 'line', [], False], [(xs_l, hs), 'line', [], False],
                [(xs_r - tb, 0), 'line', [], False]]
    return [new_stem, new_bar, None, None]


def build_J(l):
    """J: the stem runs on below the baseline into a hook that ends in a flat, vertical
    cut, like Geist Serif's J (the Slab J sat on the baseline with an up-turned stub).
    Contour [0]: 459,193 | 459,614 538,614 538,700 124,700 124,614 269,614 | 269,193
    (top slab untouched, wedged later) | hook 190,108 113,193 113,277 23,277 ... 241,-15."""
    nd = [n for n in l.paths[0].nodes]
    on = [n for n in nd if n.type != 'offcurve']
    # on-curve order: 0:459,193 1:459,614 2:538,614 3:538,700 4:124,700 5:124,614
    #                 6:269,614 7:269,193 8:190,108 9:113,193 10:113,277 11:23,277 12:23,193 13:241,-15
    xr, xl = on[0].position.x, on[7].position.x
    th = on[8].position.y - on[13].position.y           # the hook's thickness at the bottom
    xt = on[9].position.x                                # the terminal sits where the stub's inner edge was
    yo = master_by_id[l.associatedMasterId].descender
    yi = yo + th
    k = 0.552
    # one round hook: outer edge right stem -> bottom -> up to the cut; inner edge the same
    xc = (xt + xr) / 2                                   # bottom of the outer curve
    r1 = xr - xc
    lift = max(0.3 * (xc - xt), 0.35 * th)               # the cut sits a little above the bottom
    Tb = (xt, yo + lift)                                 # cut, bottom
    Tt = (xt, Tb[1] + 0.8 * th)                          # cut, top: the hook thins a little
    xci = (xt + xl) / 2                                  # bottom of the inner curve
    r2 = xl - xci
    E = (xr, yo + r1)
    Ls = (xl, yi + r2)
    top = [[P(on[i]), 'line', [], False] for i in range(1, 7)]   # 459,614 .. 269,614
    new = ([[E, 'curve', [(xc + k * r1, yo), (xr, E[1] - k * r1)], False]] + top +
           [[Ls, 'line', [], False],
            [(xci, yi), 'curve', [(xl, Ls[1] - k * r2), (xci + k * r2, yi)], False],
            [Tt, 'curve', [(xci - k * (xci - xt), yi), (xt, Tt[1] - k * max(Tt[1] - yi, 1))], False],
            [Tb, 'line', [], False],
            [(xc, yo), 'curve', [(xt, Tb[1] - k * lift), (xc - k * (xc - xt), yo)], False]])
    return [new]


def j_shift(l):
    """how far J moves left so its top-left serif sits where I's does (the hook no
    longer fills the space left of the stem above the baseline)"""
    I = next(x for x in layers(f.glyphs['I']) if x.name == l.name)
    J = next(x for x in layers(f.glyphs['J']) if x.name == l.name)
    jt = min(n.position.x for n in J.paths[0].nodes if n.position.y >= 690)
    it = min(n.position.x for n in I.paths[0].nodes if n.position.y >= 690)
    return jt - it


def shift_J(done):
    """move J (and Ĵ with its accent) left by j_shift and narrow it to match; in the
    digraphs Ǉ Ǌ move just the J part and narrow the glyph"""
    for g, l, where, d in done:
        s = J_SHIFT[l.name]
        if d == (0, 0):
            for p in l.paths:
                for nd in p.nodes:
                    nd.position = Point(nd.position.x - s, nd.position.y)
            for a in l.anchors:
                a.position = Point(a.position.x - s, a.position.y)
        else:       # the J part: its outline and its bracket pieces, all right of d
            for p in l.paths:
                if p is l.paths[where[0]] or min(nd.position.x for nd in p.nodes) >= d[0]:
                    for nd in p.nodes:
                        nd.position = Point(nd.position.x - s, nd.position.y)
        l.width -= s


def build_R(l):
    """R: the Slab's curled leg ending in an up-turned stub is replaced by a straight
    diagonal leg, K's lower leg in this layer (same angle, weight and slab feet, which
    the generic pass then wedges), ending where the old stub did and starting inside
    the bowl's bottom stroke."""
    K = next(x for x in layers(f.glyphs['K']) if x.name == l.name)
    k = [P(n) for n in K.paths[2].nodes]               # 780,0 780,88 726,88 TR TL 496,88 425,88 425,0
    xo = max(n.position.x for n in l.paths[1].nodes)   # old stub's outer edge
    dx = xo - k[0][0]
    k = [(x + dx, y) for x, y in k]
    bowl = [P(n) for n in l.paths[2].nodes]
    yc = (bowl[2][1] + bowl[17][1]) / 2                # middle of the bowl's bottom stroke

    def at(a, b, y):
        return (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)
    TR, TL = at(k[2], k[3], yc), at(k[5], k[4], yc)
    pts = [k[0], k[1], k[2], TR, TL, k[5], k[6], k[7]]
    return [[[q, 'line', [], False] for q in pts]]


if args.style == 'wedge':
    for _l in layers(f.glyphs['H']):
        lref_of(_l)        # measure H before anything is converted
    redraw('G', [1, 2, 4, 5], build_G)
    J_SHIFT = {l.name: j_shift(l) for l in layers(f.glyphs['J'])}
    shift_J(redraw('J', [0], build_J))
    redraw('R', [1], build_R)
for g in f.glyphs:
    convert_beaks(g)       # first: beaks are matched by their Slab shape
for g in f.glyphs:
    convert_slabs(g)

old = f.familyName
f.familyName = args.family
f.versionMajor, f.versionMinor = 1, 0
for inst in f.instances:
    for c in inst.customParameters:
        if c.name == 'familyName':
            c.value = c.value.replace(old, args.family)
f.save(args.out)
print(dict(report))
if partial:
    print('sites not in every layer (left as slab):', len(partial), sorted(set(partial))[:60])
