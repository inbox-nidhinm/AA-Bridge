"""How each glyph is adapted for the cell, in every weight. A glyph without a recipe
is used as drawn, centred, unless it is too wide (see default). Accented letters are not
listed: they are their base letter's result with the accents put back (see compose.py).

AA Bridge Sans has no serifs to lengthen, so the narrow letters get new ones: plain
rectangles as thick as the font's own crossbars (the f's bar for lowercase, the T's for
capitals), as in IBM Plex Mono and JetBrains Mono. Their ends sit the same distance from
the stem's centre in every weight, so every weight fills the slot the same way."""
import unicodedata
from tools import G, STEM, REG, DRAWN, S

R = {}
ALT = {}     # alternate drawings: name -> (base glyph, recipe, feature)


def recipe(*names):
    def wrap(fn):
        for n in names: R[n] = fn
        return fn
    return wrap


def alternate(name, base, feature):
    def wrap(fn):
        ALT[name] = (base, fn, feature)
        return fn
    return wrap


def _height(master, name, i):
    ys = [n[1] for n in DRAWN[master][name]['contours'][i]]
    return max(ys) - min(ys)

# The font's own horizontal strokes in each weight
BAR = {m: _height(m, 'f', 1) for m in ('Thin', 'Regular', 'Bold')}     # lowercase: the f's crossbar
CAPBAR = {m: _height(m, 'T', 1) for m in ('Thin', 'Regular', 'Bold')}  # capitals: the T's top

FLAG = 190       # a top flag reaches this far left of the stem's centre
FOOT = 225       # a foot bar reaches this far either side of the stem's centre
CAPFOOT = 225    # the I's bars and the 1's base


def box(g, x0, x1, y0, y1):
    """Add a rectangle (drawn the way the source draws its stems), before the anchors."""
    g.c.insert(g.real, [[x1, y0, 'line'], [x1, y1, 'line'], [x0, y1, 'line'], [x0, y0, 'line']])
    g.real += 1
    return g


def stem(g, i=0):
    x0, x1, y0, y1 = g.bbox([i])
    return x0, x1, (x0 + x1) / 2, y0, y1


def flag(g, i=0, top=None, at=None):
    """A bar from the stem's top-left. at=(x0, x1, top) gives the stem when it has been redrawn."""
    x0, x1, cx, _, y1 = stem(g, i) if at is None else (at[0], at[1], (at[0] + at[1]) / 2, 0, at[2])
    top = y1 if top is None else top
    return box(g, cx - FLAG, cx, top - BAR[g.master], top)


def foot(g, i=0, half=FOOT, thick=None):
    _, _, cx, _, _ = stem(g, i)
    return box(g, cx - half, cx + half, 0, BAR[g.master] if thick is None else thick)


LOWER_TARGET = 640

def default(g):
    # capitals beyond the basic set (Æ, Œ, Ŋ, Ə...) are fitted like the basic capitals;
    # anything else too wide (the Bold's widest lowercase; æ, œ, fractions, dashes) is narrowed to fit
    if not g.real: return
    u = REG[g.name]['unicode']
    if u and unicodedata.category(chr(int(u, 16))) == 'Lu': fit(g)
    elif g.width() > LOWER_TARGET: g.condense(LOWER_TARGET)


# Narrow letters: flags and feet, as sans monospaces do.
@recipe('i', 'idotless', 'idotaccent')
def i(g):
    x0, x1, cx, _, y1 = stem(g, 0)
    flag(g, 0)
    foot(g, 0)
    g.offset = 8

@recipe('j', 'jdotless')
def j(g):
    # a flag like the i's; the hook keeps its drawing
    flag(g, 0, top=stem(g, 0)[4])


def _tail(master):
    """The t's stem and curled tail, without its crossbar: the l's lower half."""
    t = DRAWN[master]['t']['contours'][0]
    return t, [n[:] for n in t[:12]], t[21:]

@recipe('l')
def l(g):
    # a flag and a foot, as on the i (and as AA Bridge Slab Mono's l)
    flag(g, 0)
    foot(g, 0)
    g.offset = 8

@alternate('l.tail', 'l', 'ss05')
def l_tail(g):
    # the t's curled tail under a full-height stem
    t, tail, rest = _tail(g.master)
    x0, x1, cx, _, top = stem(g, 0)
    right = t[11][0]                      # the t's stem, right side
    dx = x1 - right                       # put the t's stem where the l's is
    left = t[21][0]
    new = tail + [[right, top, 'line'], [left, top, 'line']] + [n[:] for n in rest]
    g.c[0] = [[x + dx, y, k] for x, y, k in new]
    flag(g, at=(x0, x1, top))
    g.offset = -20

@recipe('r')
def r(g):
    # the arm reaches a little further; a flag and a foot as on the i
    g.like_regular(lambda r: r.xmap([(250, 250), (390, 425)], idx=[1]))
    flag(g, 0)
    foot(g, 0)

@alternate('r.plain', 'r', 'ss06')
def r_plain(g):
    # no foot: a longer arm and a flag
    g.like_regular(lambda r: r.xmap([(220, 220), (390, 470)], idx=[1]))
    flag(g, 0)
    g.offset = 10

@recipe('f')
def f(g):
    # the crossbar reaches as far left of the stem as it does right
    g.like_regular(lambda r: r.xmap([(35, -5), (420, 440)], idx=[1]))

@recipe('I')
def I(g):
    _, _, cx, y0, y1 = stem(g, 0)
    b = CAPBAR[g.master]
    box(g, cx - CAPFOOT, cx + CAPFOOT, y1 - b, y1)
    box(g, cx - CAPFOOT, cx + CAPFOOT, y0, y0 + b)

@recipe('J')
def J(g):
    # a bar to the left at the top; the hook keeps its drawing
    xs = [n[0] for n in g.c[0] if n[1] >= 699]
    x0, x1 = min(xs), max(xs)
    box(g, (x0 + x1) / 2 - CAPFOOT, x1, 700 - CAPBAR[g.master], 700)

@recipe('one')
def one(g):
    # a base under the stem
    xs = [n[0] for n in g.c[0] if abs(n[1]) < 1]
    cx = (min(xs) + max(xs)) / 2
    box(g, cx - CAPFOOT, cx + CAPFOOT, 0, CAPBAR[g.master])


# Wide letters: counters narrow, stems keep their weight.
@recipe('m')
def m(g): g.condense(600, keep=0.82)

@recipe('w')
def w(g): g.condense(640, keep=0.85)

@recipe('W')
def W(g): g.condense(660, keep=0.8)

@recipe('M')
def M(g):
    # vertical legs stay; the V is narrowed with them and its point lifted off the baseline
    g.condense(600, keep=0.85)
    g.ymap([(0, 130), (700, 700)], idx=[0])
    g.center_anchors()

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


# Code needs these to be told apart: the slashed zero, and straight quotes drawn as
# upright wedges in place of the curly ones. The slashed and plain zeros swap places,
# so the plain one is the alternate (Stylistic Set 4, see build.py).
SOURCE = {k: v for k, v in {'zero': 'zero.zero', 'zero.zero': 'zero',
                            'zero.lf': 'zero.lf.zero', 'zero.lf.zero': 'zero.lf'}.items() if k in REG and v in REG}

def wedge(cx, stem, top=700, bottom=440):
    wt, wb = stem * 0.93, stem * 0.45
    return [[cx - wb / 2, bottom, 'line'], [cx + wb / 2, bottom, 'line'],
            [cx + wt / 2, top, 'line'], [cx - wt / 2, top, 'line']]

@recipe('quotesingle')
def quotesingle(g):
    g.set_contours([wedge(345, STEM[g.master])])

@recipe('quotedbl')
def quotedbl(g):
    stem_ = STEM[g.master]
    apart = stem_ * 0.93 / 2 + 37
    g.set_contours([wedge(345 - apart, stem_), wedge(345 + apart, stem_)])


@recipe('slash', 'backslash')
def long_slash(g):
    # code fonts run the slashes from below the baseline to above the capitals;
    # lengthened along their own angle, so the stroke keeps its weight
    x0, x1, y0, y1 = g.bbox()
    foot_ = [n[0] for c in g.c for n in c if abs(n[1] - y0) < 1]
    w = max(foot_) - min(foot_)
    run = (x1 - x0 - w) / (y1 - y0) * (1 if g.name == 'slash' else -1)
    ym = (y0 + y1) / 2
    k = (790 + 140) / (y1 - y0)
    for c in g.c:
        for n in c:
            d = n[1] - ym
            n[0] += d * (k - 1) * run
            n[1] = ym + d * k + (325 - ym)


@recipe('ellipsis')
def ellipsis(g):
    # three of the period's dots (80%, smaller in the Bold), spread evenly across the slot
    dot = DRAWN[g.master]['period']['contours'][0]
    xs, ys = [n[0] for n in dot], [n[1] for n in dot]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    k_ = min(0.8, 160 / (max(xs) - min(xs)))
    w = (max(xs) - min(xs)) * k_
    step = (640 - w) / 2
    g.set_contours([[[300 / S + k * step + (n[0] - cx) * k_, cy + (n[1] - cy) * k_, n[2]] for n in dot]
                    for k in (-1, 0, 1)])
