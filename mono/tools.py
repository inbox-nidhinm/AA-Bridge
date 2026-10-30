"""Working on the original Trupeer Slab Regular drawings (the 16pt {378} layer).
Everything here is in the original's units; the build scales by S into the 600-unit cell."""
import copy
from source import load

REG = load('{378,16}')    # the Regular, 16pt optical size
BOLD = load('Bold 16pt')

S = 0.87                 # design scale: the original's n fits the cell unchanged
CELL = 600 / S           # the cell in the original's units
STEM_R, STEM_B = 103, 182  # lowercase stem, Regular and Bold 16pt


class G:
    def __init__(self, name):
        self.name = name
        self.c = copy.deepcopy(REG[name]['contours'])
        self.b = copy.deepcopy(BOLD[name]['contours'])
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

    def condense(self, target=None, sx=None, idx=None, stem=STEM_R, keep=1.0):
        """Narrow by moving x towards the Bold drawing first, so stems keep their weight
        while counters and serifs get narrower. Uses the same contours of the Bold layer."""
        idx = set(range(len(self.c))) if idx is None else set(idx)
        reg = [[n[:] for n in c] for c in self.c]
        def at(t):
            return [[(r[0] + t * (b[0] - r[0])) for r, b in zip(rc, bc)] if i in idx else None
                    for i, (rc, bc) in enumerate(zip(reg, self.b))]
        t = 0.0
        for _ in range(12):
            xs = at(t)
            allx = [x for i, c in enumerate(xs) if c for x in c]
            w = max(allx) - min(allx)
            k = sx if sx else target / w
            t = max(0.0, (stem * keep / k - stem) / (STEM_B - STEM_R))
        xs = at(t)
        allx = [x for c in xs if c for x in c]
        x0 = min(allx)
        rx = [n[0] for i in idx for n in reg[i]]
        left = min(rx)
        for i in idx:
            for n, x in zip(self.c[i], xs[i]):
                n[0] = left + (x - x0) * k
        self.t = t
        return self

    def add(self, other, idx=None, dx=0, dy=0):
        for i, c in enumerate(other.c):
            if idx is None or i in idx:
                self.c.append([[n[0] + dx, n[1] + dy, n[2]] for n in c])
        return self

    def drop(self, idx):
        self.c = [c for i, c in enumerate(self.c) if i not in idx]
        return self

    def final(self):
        """Scale into the cell and centre the ink."""
        x0, x1, _, _ = self.bbox()
        mid = (x0 + x1) / 2
        out = []
        for c in self.c:
            out.append([(round((n[0] - mid + self.offset) * S + 300), round(n[1] * S), n[2]) for n in c])
        return out
