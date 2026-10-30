"""Working on the original Trupeer Slab drawings (its 16pt optical size), one weight at a time.
Everything here is in the original's units; the build scales by S into the 600-unit cell."""
import copy
from source import load

# The weights the family is built from, and the layers of the original they come from.
# The original's Bold ('Heavy' here) is too heavy for the cell, so the mono's Bold sits
# BOLD_AT of the way from the original's Regular to it, as monospace bolds are lighter.
LAYERS = {'Thin': 'Thin 16pt', 'Regular': '{378,16}', 'Heavy': 'Bold 16pt'}
DRAWN = {m: load(layer) for m, layer in LAYERS.items()}
REG = DRAWN['Regular']
BOLD_AT = 0.8


def _between(a, b, t):
    return {n: dict(a[n], contours=[[[p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]), p[2]]
                                      for p, q in zip(pc, qc)]
                                     for pc, qc in zip(a[n]['contours'], b[n]['contours'])])
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


class G:
    def __init__(self, name, master='Regular'):
        self.name, self.master = name, master
        self.c = copy.deepcopy(DRAWN[master][name]['contours'])
        self.offset = 0      # optical shift (original units) after centring

    # geometry
    def nodes(self, idx=None):
        for i, c in enumerate(self.c):
            if idx is None or i in idx:
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

    def condense(self, target=None, sx=None, idx=None, keep=1.0):
        """Narrow by moving x towards a heavier drawing first, so stems keep their weight
        (times keep) while counters and serifs get narrower."""
        idx = set(range(len(self.c))) if idx is None else set(idx)
        lo, hi, t0 = PAIR[self.master]
        own = [[n[:] for n in c] for c in self.c]
        light = own if lo == self.master else DRAWN[lo][self.name]['contours']
        heavy = own if hi == self.master else DRAWN[hi][self.name]['contours']
        s_lo, s_hi, s_own = STEM[lo], STEM[hi], STEM[self.master]
        def at(t):
            return [[l[0] + t * (h[0] - l[0]) for l, h in zip(lc, hc)] if i in idx else None
                    for i, (lc, hc) in enumerate(zip(light, heavy))]
        t = t0
        for _ in range(12):
            xs = at(t)
            allx = [x for c in xs if c for x in c]
            k = sx if sx else target / (max(allx) - min(allx))
            t = min(max(t0, (s_own * keep / k - s_lo) / (s_hi - s_lo)), 1 + REACH)
        xs = at(t)
        x0 = min(x for c in xs if c for x in c)
        left = min(n[0] for i in idx for n in own[i])
        for i in idx:
            for n, x in zip(self.c[i], xs[i]):
                n[0] = left + (x - x0) * k
        self.t = t
        return self

    def final(self):
        """Scale into the cell and centre the ink."""
        x0, x1, _, _ = self.bbox()
        mid = (x0 + x1) / 2
        out = []
        for c in self.c:
            out.append([(round((n[0] - mid + self.offset) * S + 300), round(n[1] * S), n[2]) for n in c])
        return out
