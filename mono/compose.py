"""Accented letters. The source draws them as plain outlines, so each one is matched against
its base letter: if every contour of the base is there (moved by the same amount), the rest
are its accents. The mono then draws the base as the base's own result and puts each accent
back where it sat against the base's nearest anchor, now wherever that anchor ended up."""
import unicodedata
from tools import DRAWN, REG, S, anchor_names

TOLERANCE = 3
LETTER = 450    # accents are shorter than this; a second letter is not
CMAP = {int(g['unicode'], 16): n for n, g in REG.items() if g['unicode']}


def candidates(name):
    """Bases to try: the Unicode decomposition's first character, else the name's first letter;
    before i and j, their dotless forms (accents replace the dot)."""
    out = []
    u = REG[name]['unicode']
    if u:
        d = unicodedata.decomposition(chr(int(u, 16)))
        if d and not d.startswith('<') and int(d.split()[0], 16) in CMAP:
            out.append(CMAP[int(d.split()[0], 16)])
    stem = name.split('.')[0]
    if len(stem) > 1 and stem[0].isalpha():
        out.append(stem[0])
    seen = []
    for b in out:
        for c in ([b + 'dotless'] if b in ('i', 'j') else []) + [b]:
            if c in REG and c != name and c not in seen: seen.append(c)
    return seen


def match(name, base, master):
    """The shift that puts every base contour onto a contour of the glyph, and the leftovers."""
    glyph, parts = DRAWN[master][name]['contours'], DRAWN[master][base]['contours']
    if not parts or len(parts) >= len(glyph): return None
    def fits(c, p, d):
        return len(c) == len(p) and all(abs(a[0] - b[0] - d[0]) <= TOLERANCE and abs(a[1] - b[1] - d[1]) <= TOLERANCE
                                        for a, b in zip(c, p))
    for c in glyph:
        if len(c) != len(parts[0]): continue
        d = (c[0][0] - parts[0][0][0], c[0][1] - parts[0][0][1])
        used = set()
        for p in parts:
            hit = next((i for i, g in enumerate(glyph) if i not in used and fits(g, p, d)), None)
            if hit is None: break
            used.add(hit)
        else:
            return d, [i for i in range(len(glyph)) if i not in used]
    return None


def nearest(anchors, point):
    if not anchors: return None
    return min(anchors, key=lambda a: (anchors[a][0] - point[0]) ** 2 + (anchors[a][1] - point[1]) ** 2)


def find(names):
    """name -> (base, [(contour index, anchor name or None)]) for every accented glyph."""
    out = {}
    for name in names:
        for base in candidates(name):
            m = match(name, base, 'Regular')
            if not m or any(match(name, base, w) is None for w in ('Thin', 'Heavy')): continue
            d, extra = m
            # a second letter (the LJ, Dž digraphs) is not an accent: those are fitted whole
            box = [n for i in extra for n in REG[name]['contours'][i]]
            # (height alone decides: the Sans's j is too narrow to be told apart by width)
            if max(n[1] for n in box) - min(n[1] for n in box) > LETTER: continue
            anchors = REG[base]['anchors']
            marks = []
            for i in extra:
                c = REG[name]['contours'][i]
                xs, ys = [n[0] for n in c], [n[1] for n in c]
                marks.append((i, nearest(anchors, ((min(xs) + max(xs)) / 2 - d[0], (min(ys) + max(ys)) / 2 - d[1]))))
            out[name] = (base, marks)
            break
    return out


def assemble(name, master, structure, base_result):
    """Draw an accented glyph from its base's finished contours and anchors (in cell units)."""
    base, marks = structure
    contours, placed, base_mid = base_result
    d = match(name, base, master)[0]
    src = DRAWN[master]
    out = [list(c) for c in contours]
    for i, a in marks:
        if a is not None and a in placed:
            ox, oy = src[base]['anchors'][a]
            nx, ny = placed[a]
        else:   # no anchor: keep the accent's place against the base's centre
            bx = [n[0] for c in src[base]['contours'] for n in c]
            ox, oy = (min(bx) + max(bx)) / 2, 0
            nx, ny = base_mid, 0
        out.append([(round(nx + (x - d[0] - ox) * S), round(ny + (y - d[1] - oy) * S), t)
                    for x, y, t in src[name]['contours'][i]])
    # the accented glyph's own anchors follow the base's, or the nearest one
    anchors = {}
    for a in anchor_names(name):
        x, y = src[name]['anchors'][a]
        ref = a if a in placed else nearest({k: src[base]['anchors'][k] for k in placed}, (x - d[0], y - d[1]))
        if ref is None: continue
        ox, oy = src[base]['anchors'][ref]
        anchors[a] = (placed[ref][0] + (x - d[0] - ox) * S, placed[ref][1] + (y - d[1] - oy) * S)
    return out, anchors
