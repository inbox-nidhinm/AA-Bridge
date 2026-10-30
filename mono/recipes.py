"""How each glyph is adapted for the cell, in every weight. A glyph without a recipe
is used as drawn, centred, unless it is too wide (see default)."""
from tools import G, STEM

R = {}

def recipe(*names):
    def wrap(fn):
        for n in names: R[n] = fn
        return fn
    return wrap


def same_change(*names):
    """A change written for the Regular and made the same way in every weight."""
    def wrap(fn):
        for n in names: R[n] = lambda g, fn=fn: g.like_regular(fn)
        return fn
    return wrap


LOWER_TARGET = 660

def default(g):
    # the Bold's widest lowercase (a, n, p) are a little too wide for the cell
    if g.width() > LOWER_TARGET: g.condense(LOWER_TARGET)


# Narrow letters: longer slabs, as typewriter monospaces do.
@same_change('i')
def i(g):
    g.xmap([(41, -80), (86, 86), (275, 275), (310, 420)]); g.offset = 10

@same_change('l')
def l(g):
    g.xmap([(34, -85), (80, 80), (266, 266), (301, 425)]); g.offset = 10

@same_change('j')
def j(g):
    # only the top serif grows (to the i's length); the hook keeps its drawing
    g.xmap([(54, -46), (94, 94)], idx=[0], above=400)

@same_change('r')
def r(g):
    g.xmap([(41, 5), (86, 86), (275, 275), (350, 450)], idx=[0])
    g.xmap([(240, 240), (400, 450)], idx=[1])

@same_change('f')
def f(g):
    g.xmap([(69, -5), (115, 115), (297, 297), (372, 440)], idx=[0])
    g.xmap([(35, -40), (420, 490)], idx=[1])
    g.xmap([(257, 257), (373, 410)], idx=[2])
    g.shift(37, idx=[3])

@same_change('t')
def t(g):
    g.xmap([(-1000, -1045), (70, 25), (149, 149)], idx=[0])
    g.xmap([(400, 400), (510, 570)], idx=[1])

@same_change('I')
def I(g):
    g.xmap([(27, -60), (90, 90), (277, 277), (340, 430)])

@same_change('J')
def J(g):
    # only the top serif grows; the hook keeps its drawing
    g.xmap([(262, 180), (342, 342), (529, 529), (582, 640)], idx=[0], above=600)

@same_change('one')
def one(g):
    g.xmap([(106, 10), (190, 190), (374, 374), (429, 520)], idx=[0, 2, 3])


# Wide letters: counters and serifs narrow, stems keep their weight.
@recipe('m')
def m(g): g.condense(680, keep=0.85)

@recipe('w')
def w(g): g.condense(680, keep=0.88)

@recipe('W')
def W(g): g.condense(690, keep=0.85)

@recipe('M')
def M(g):
    # vertical legs stay; the V is narrowed and its point lifted, as in Courier and Plex Mono
    d = 290
    def legs(r):
        r.xmap([(31, 61), (86, 86)], idx=[1, 3, 4, 7])
        r.xmap([(950, 950), (1005, 975)], idx=[2, 6, 8, 5])
        r.shift(-d, idx=[2, 5, 6, 8])
    g.like_regular(legs, idx=range(1, 9))
    g.condense(g.width([0]) - d, idx=[0], keep=0.85)
    g.ymap([(0, 170), (700, 700)], idx=[0])

CAP_TARGET = 610

def fit(g, target=CAP_TARGET, keep=0.95):
    if g.width() > target: g.condense(target, keep=keep)

for n in ('U', 'H', 'N', 'A', 'V', 'X', 'Y', 'K', 'R', 'T', 'Z', 'B', 'P', 'E', 'F', 'L', 'S'):
    R.setdefault(n, fit)

@recipe('Q')
def Q(g): fit(g, 650)

@recipe('O', 'C', 'G', 'D')
def round_cap(g): fit(g, 600)

@recipe('ampersand', 'at', 'percent')
def wide_symbol(g): fit(g, 660)

@recipe('underscore')
def underscore(g):
    x0, x1, _, _ = g.bbox(); g.xmap([(x0, -10), (x1, 680)])


# Code needs these to be told apart: the original's slashed zero, and straight quotes
# drawn as upright wedges in place of the original's curly ones.
SOURCE = {'zero': 'zero.zero'}

def wedge(cx, stem, top=700, bottom=440):
    wt, wb = stem * 0.93, stem * 0.45
    return [[cx - wb / 2, bottom, 'line'], [cx + wb / 2, bottom, 'line'],
            [cx + wt / 2, top, 'line'], [cx - wt / 2, top, 'line']]

@recipe('quotesingle')
def quotesingle(g):
    g.c = [wedge(345, STEM[g.master])]

@recipe('quotedbl')
def quotedbl(g):
    stem = STEM[g.master]
    apart = stem * 0.93 / 2 + 37
    g.c = [wedge(345 - apart, stem), wedge(345 + apart, stem)]


@recipe('slash', 'backslash')
def long_slash(g):
    # code fonts run the slashes from below the baseline to above the capitals;
    # lengthened along their own angle, so the stroke keeps its weight
    x0, x1, y0, y1 = g.bbox()
    foot = [n[0] for c in g.c for n in c if abs(n[1] - y0) < 1]
    w = max(foot) - min(foot)
    run = (x1 - x0 - w) / (y1 - y0) * (1 if g.name == 'slash' else -1)
    ym = (y0 + y1) / 2
    k = (790 + 140) / (y1 - y0)
    for c in g.c:
        for n in c:
            d = n[1] - ym
            n[0] += d * (k - 1) * run
            n[1] = ym + d * k + (325 - ym)
