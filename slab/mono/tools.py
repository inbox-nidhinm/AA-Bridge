"""Working on the original Trupeer Slab drawings (its 16pt optical size), one weight at a time.
Everything here is in the original's units; the build scales by S into the 600-unit cell."""
import copy
import math
import fillets
from source import load

# The weights the family is built from, and the layers of the original they come from.
# The original's Bold ('Heavy' here) is too heavy for the cell, so the mono's Bold sits
# BOLD_AT of the way from the original's Regular to it, as monospace bolds are lighter.
LAYERS = {'Thin': 'Thin 16pt', 'Regular': '{378,16}', 'Heavy': 'Bold 16pt'}
DRAWN = {m: load(layer) for m, layer in LAYERS.items()}
REG = DRAWN['Regular']
BOLD_AT = 0.8


def _between(a, b, t):
    mix = lambda p, q: [p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])]
    return {n: dict(a[n], contours=[[mix(p, q) + [p[2]] for p, q in zip(pc, qc)]
                                     for pc, qc in zip(a[n]['contours'], b[n]['contours'])],
                    anchors={k: mix(v, b[n]['anchors'][k]) for k, v in a[n]['anchors'].items() if k in b[n]['anchors']})
            for n in a if n in b and [len(c) for c in a[n]['contours']] == [len(c) for c in b[n]['contours']]}


DRAWN['Bold'] = _between(REG, DRAWN['Heavy'], BOLD_AT)
MASTERS = ('Thin', 'Regular', 'Bold')

S = 0.87                 # design scale: the original's n fits the cell unchanged
CELL = 600 / S           # the cell in the original's units
STEM = {'Thin': 35, 'Regular': 103, 'Heavy': 182}  # lowercase stem of each drawing
STEM['Bold'] = STEM['Regular'] + BOLD_AT * (STEM['Heavy'] - STEM['Regular'])

# Narrowing moves x towards a heavier drawing first: (lighter, heavier, where this weight sits).
# Past the original's Bold there is nothing heavier, so it may reach beyond it by REACH.
PAIR = {'Thin': ('Thin', 'Regular', 0.0), 'Regular': ('Regular', 'Heavy', 0.0),
        'Bold': ('Regular', 'Heavy', BOLD_AT)}
REACH = 0.35


def anchor_names(name):
    """The anchors a glyph has in every drawing, so all weights carry the same ones."""
    sets = [set(DRAWN[m][name]['anchors']) for m in ('Thin', 'Regular', 'Heavy') if name in DRAWN[m]]
    return sorted(set.intersection(*sets)) if sets else []


def outline(master, name):
    """A glyph's contours, then its anchors as one-node contours, so every change moves them too."""
    g = DRAWN[master][name]
    return ([[n[:] for n in c] for c in g['contours']] +
            [[list(g['anchors'][a]) + ['anchor']] for a in anchor_names(name)])


# The original cuts the points of A M N V W v w at PEN (rising to the right): the corner on
# the overshoot sits on one stroke edge, the other corner where the cut meets the other edge.
PEN = math.radians(30)


def find_cuts(contours):
    """The original's angled cuts in a drawing: for each, the nodes on its two corners and
    between them (as (contour, node) pairs), and the node that ends the stroke edge the
    corner off the overshoot sits on."""
    tan = math.tan(PEN)
    on = [(ci, ni) for ci, c in enumerate(contours) for ni, n in enumerate(c) if n[2] != 'offcurve']
    at = lambda r: contours[r[0]][r[1]]
    spans = {}       # each cut's line (its height at x = 0) -> its x extent
    for ci, c in enumerate(contours):
        for ni, n in enumerate(c):
            m = c[(ni + 1) % len(c)]
            if n[2] == 'offcurve' or m[2] != 'line' or abs(m[0] - n[0]) < 5: continue
            if abs(math.degrees(math.atan2(m[1] - n[1], m[0] - n[0])) % 180 - 30) > 0.5: continue
            if 150 < min(n[1], m[1]) and max(n[1], m[1]) < 550: continue     # points only
            k = n[1] - n[0] * tan
            key = next((k2 for k2 in spans if abs(k - k2) < 1), k)
            x0, x1 = spans.get(key, (math.inf, -math.inf))
            spans[key] = (min(x0, n[0], m[0]), max(x1, n[0], m[0]))
    cuts = []
    for k, (x0, x1) in spans.items():
        nodes = [r for r in on if abs(at(r)[1] - at(r)[0] * tan - k) * math.cos(PEN) < 0.75
                 and x0 - 0.75 <= at(r)[0] <= x1 + 0.75]
        top = at(nodes[0])[1] > 300
        lo = [r for r in nodes if abs(at(r)[0] - x0) < 0.75]
        hi = [r for r in nodes if abs(at(r)[0] - x1) < 0.75]
        mid = [(r, (at(r)[0] - x0) / (x1 - x0)) for r in nodes if r not in lo and r not in hi]

        def edge(corner, side):
            # the stroke edge leaving the corner on the outside of the point
            best = None
            for ci, ni in corner:
                c = contours[ci]
                for nb in ((ci, (ni - 1) % len(c)), (ci, (ni + 1) % len(c))):
                    p, q = at((ci, ni)), at(nb)
                    dx, dy = q[0] - p[0], q[1] - p[1]
                    if q[2] == 'offcurve' or abs(q[1] - q[0] * tan - k) < 1: continue
                    if (dy < 20) if not top else (dy > -20): continue
                    if dx * side < -0.5: continue          # must open away from the point
                    s = dx / abs(dy) * side
                    if best is None or s > best[0]: best = (s, nb)
            return best and best[1]
        # bottom points keep their low (left) corner and slide the right one; the A's apex
        # keeps its high (right) corner and slides the left one
        moving, side = (lo, -1) if top else (hi, 1)
        nb = edge(moving, side)
        if lo and hi and nb:
            cuts.append(dict(fixed=hi if top else lo, moving=moving, edge=nb, mid=mid, lo=lo, hi=hi))
    return cuts


class G:
    def __init__(self, name, master='Regular'):
        self.name, self.master = name, master
        self.c = outline(master, name)
        self.real = len(DRAWN[master][name]['contours'])   # the rest are anchors
        self.anchors = anchor_names(name)
        self.offset = 0      # optical shift (original units) after centring

    def set_contours(self, contours):
        self.c, self.real, self.anchors = contours, len(contours), []

    # geometry (of the drawing; anchors never count)
    def nodes(self, idx=None):
        for i, c in enumerate(self.c):
            if (i < self.real) if idx is None else (i in idx):
                yield from c

    def bbox(self, idx=None):
        xs = [n[0] for n in self.nodes(idx)]
        ys = [n[1] for n in self.nodes(idx)]
        return min(xs), max(xs), min(ys), max(ys)

    def width(self, idx=None):
        x0, x1, _, _ = self.bbox(idx)
        return x1 - x0

    # operations
    def xmap(self, knots, idx=None, above=None):
        """Piecewise-linear map of x (knots: [(old, new), ...]); slope 1 outside.
        With above, only nodes at or above that height move."""
        knots = sorted(knots)
        def f(x):
            if x <= knots[0][0]: return x + knots[0][1] - knots[0][0]
            if x >= knots[-1][0]: return x + knots[-1][1] - knots[-1][0]
            for (a, fa), (b, fb) in zip(knots, knots[1:]):
                if a <= x <= b: return fa + (x - a) * (fb - fa) / (b - a)
        for i, c in enumerate(self.c):
            if idx is None or i in idx:
                for n in c:
                    if above is None or n[1] >= above: n[0] = f(n[0])
        return self

    def ymap(self, knots, idx=None):
        knots = sorted(knots)
        def f(y):
            if y <= knots[0][0]: return y + knots[0][1] - knots[0][0]
            if y >= knots[-1][0]: return y + knots[-1][1] - knots[-1][0]
            for (a, fa), (b, fb) in zip(knots, knots[1:]):
                if a <= y <= b: return fa + (y - a) * (fb - fa) / (b - a)
        for i, c in enumerate(self.c):
            if idx is None or i in idx:
                for n in c: n[1] = f(n[1])
        return self

    def shift(self, dx, dy=0, idx=None):
        for i, c in enumerate(self.c):
            if idx is None or i in idx:
                for n in c: n[0] += dx; n[1] += dy
        return self

    def like_regular(self, fn, idx=None):
        """Make the change fn makes to the Regular: every node moves as its Regular twin does,
        so a serif lengthened by 100 in the Regular is lengthened by 100 in every weight."""
        r = G(self.name, 'Regular')
        before = copy.deepcopy(r.c)
        fn(r)
        for i, (c, after, was) in enumerate(zip(self.c, r.c, before)):
            if idx is None or i in idx:
                for n, a, b in zip(c, after, was):
                    n[0] += a[0] - b[0]; n[1] += a[1] - b[1]
        self.offset = r.offset
        return self

    def condense(self, target=None, sx=None, idx=None, keep=1.0, measure=None):
        """Narrow by moving x towards a heavier drawing first, so stems keep their weight
        (times keep) while counters and serifs get narrower. With measure, only those
        contours set the width and left edge; the rest of idx follows them."""
        idx = set(range(len(self.c))) if idx is None else set(idx)
        lo, hi, t0 = PAIR[self.master]
        own = [[n[:] for n in c] for c in self.c]
        light = own if lo == self.master else outline(lo, self.name)
        heavy = own if hi == self.master else outline(hi, self.name)
        drawn = [i for i in (idx if measure is None else measure) if i < self.real]
        s_lo, s_hi, s_own = STEM[lo], STEM[hi], STEM[self.master]
        def at(t):
            return [[l[0] + t * (h[0] - l[0]) for l, h in zip(lc, hc)] if i in idx else None
                    for i, (lc, hc) in enumerate(zip(light, heavy))]
        t = t0
        for _ in range(12):
            xs = at(t)
            allx = [x for i in drawn for x in xs[i]]
            k = sx if sx else target / (max(allx) - min(allx))
            t = min(max(t0, (s_own * keep / k - s_lo) / (s_hi - s_lo)), 1 + REACH)
        xs = at(t)
        x0 = min(x for i in drawn for x in xs[i])
        left = min(n[0] for i in drawn for n in own[i])
        for i in idx:
            for n, x in zip(self.c[i], xs[i]):
                n[0] = left + (x - x0) * k
        self.t = t
        return self

    def refit(self):
        """After narrowing, lay the original's joint fillets back into their corners."""
        if hasattr(self, 't'):
            fillets.refit(self.c, DRAWN[self.master][self.name]['contours'], self.real)
        return self

    def recut(self):
        """Narrowing a letter steepens the original's cut on its point, so it is cut again at
        PEN: the corner on the overshoot stays, the other slides along its stroke edge."""
        drawing = DRAWN[self.master][self.name]['contours']
        if self.real != len(drawing): return self
        d = (math.cos(PEN), math.sin(PEN))
        for cut in find_cuts(drawing):
            at = lambda r: self.c[r[0]][r[1]]
            p, a, b = at(cut['fixed'][0]), at(cut['moving'][0]), at(cut['edge'])
            ex, ey = b[0] - a[0], b[1] - a[1]
            t = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / (d[0] * ey - d[1] * ex)
            new = (p[0] + d[0] * t, p[1] + d[1] * t)
            for r in cut['moving']: at(r)[:2] = new
            l, h = at(cut['lo'][0]), at(cut['hi'][0])
            for r, s in cut['mid']: at(r)[:2] = [l[0] + s * (h[0] - l[0]), l[1] + s * (h[1] - l[1])]
        return self

    def center_anchors(self, names=('top', 'bottom', 'center')):
        x0, x1, _, _ = self.bbox()
        for i, a in enumerate(self.anchors):
            if a in names: self.c[self.real + i][0][0] = (x0 + x1) / 2
        return self

    def final(self):
        """Scale into the cell and centre the ink. The anchors land in self.placed."""
        x0, x1, _, _ = self.bbox() if self.real else (300 / S, 300 / S, 0, 0)
        mid = (x0 + x1) / 2
        place = lambda n: ((n[0] - mid + self.offset) * S + 300, n[1] * S)
        self.placed = {a: place(self.c[self.real + i][0]) for i, a in enumerate(self.anchors)}
        return [[tuple(round(v) for v in place(n)) + (n[2],) for n in c] for c in self.c[:self.real]]
