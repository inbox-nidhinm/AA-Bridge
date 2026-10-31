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
    L0, t0, k = s['L0'], s['t0'], s['k']
    d = W_DROP * t0 if head else 0
    wt = min(1.0, max(0.0, (t0 - 16) / 78))
    climb = (W_HEAD_H * (1 - wt) + W_HEAD_H_BOLD * wt) if head else (W_H * (1 - wt) + W_H_BOLD * wt)
    h = d + climb * t0 / (1 + W_SLANT * abs(k))
    h = min(h, s['run'] * 0.8 + t0)
    tip = (L0, d)
    S = (k * h, h)
    corner = (k * d, d)
    m1 = (tip[0] + (S[0] - tip[0]) / 3, tip[1] + (S[1] - tip[1]) / 3)
    m2 = (tip[0] + (S[0] - tip[0]) * 2 / 3, tip[1] + (S[1] - tip[1]) * 2 / 3)
    c1 = (m1[0] + W_CONC * (corner[0] - m1[0]), m1[1] + W_CONC * (corner[1] - m1[1]))
    c2 = (m2[0] + W_CONC * (corner[0] - m2[0]), m2[1] + W_CONC * (corner[1] - m2[1]))
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
                    want = {(s['Y0'], round(s['X0'])) for s in fw}
                    fw = [s for s in find_sites(pts) if (s['Y0'], round(s['X0'])) in want]
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


def redo_beak(l, p):
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


def narrow_spur(l, p, cx):
    """thin tip, and the inner edge becomes a bracket sweeping up into the stroke"""
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
    for pi in range(npaths):
        sigs = {sig(l.paths[pi]) for l in ls if pi < len(l.paths)}
        if len(sigs) != 1:
            continue
        s = sigs.pop()
        if s in ('llllooc', 'lloocll'):
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
    for pi in sorted(spur_fillets, reverse=True):
        for l in ls:
            del l.paths[pi]
    report['spur fillets'] += len(spur_fillets)


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
