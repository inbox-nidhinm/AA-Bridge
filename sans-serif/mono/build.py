"""Builds Trupeer Sans Mono, Thin to Bold: python build.py

Draws the Thin, Regular and Bold masters into build/ as UFOs with a designspace, then
makes the variable font (fonts/variable) and seven static weights (fonts/ttf, fonts/otf)."""
import os, re, subprocess, sys
import glyphsLib, ufoLib2
from ufoLib2.objects import Anchor
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor
from tools import G, REG, S, STEM, MASTERS
from recipes import R, ALT, SOURCE, default
from source import SOURCE as GLYPHS_FILE
import compose

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
FONTS = os.path.join(HERE, 'fonts')
FAMILY = 'Trupeer Sans Mono'

# The original's weight axis: user value -> where the drawings sit (its Regular is drawn at 378)
AXIS_MAP = [(100, 100), (200, 180), (300, 260), (400, 378), (500, 492), (600, 588), (700, 700)]
WEIGHTS = {'Thin': 100, 'ExtraLight': 200, 'Light': 300, 'Regular': 400, 'Medium': 500, 'SemiBold': 600, 'Bold': 700}
MASTER_AT = {'Thin': 100, 'Regular': 378, 'Bold': 700}
X_HEIGHT = {'Thin': 517, 'Regular': 529, 'Bold': 539}
FEATURE_NAMES = {'ss05': 'Curled-tail l', 'ss06': 'r without a foot'}
ZERO_SET = 'ss04'      # the original uses ss01 to ss03 (tilted o, other a, other g)

# The original's OpenType features and glyph categories, as glyphsLib writes them
_ORIGINAL = glyphsLib.to_designspace(glyphsLib.GSFont(GLYPHS_FILE), minimal=True).sources[0].font
CATEGORIES = dict(_ORIGINAL.lib.get('public.openTypeCategories', {}))
# Monospace practice: no ligatures (they would join two letters into one slot)
LIGATURES = {n for n, c in CATEGORIES.items() if c == 'ligature'}
MARKS = {n for n, c in CATEGORIES.items() if c == 'mark'}     # combining: no width
NAMES = [n for n in REG if n not in LIGATURES and n != '.notdef']
STRUCTURE = compose.find([n for n in NAMES if n not in MARKS and n not in R])


def features():
    fea = _ORIGINAL.features.text
    fea = re.sub(r'feature liga \{.*?\} liga;\n*', '', fea, flags=re.S)
    # the slashed zero is the default here, so the original's slashed-zero switch becomes
    # a set that gives the plain one back
    fea = fea.replace('feature zero;\n', '')
    fea = fea.replace('feature zero {', f'feature {ZERO_SET} {{\nfeatureNames {{ name "Plain zero"; }};')
    fea = fea.replace('} zero;', f'}} {ZERO_SET};')
    # the mono's own alternates, one stylistic set each
    for feat in sorted({a[2] for a in ALT.values()}):
        subs = ''.join(f'sub {base} by {name};\n' for name, (base, _, ft) in ALT.items() if ft == feat)
        fea += f'\nfeature {feat} {{\nfeatureNames {{ name "{FEATURE_NAMES[feat]}"; }};\n{subs}}} {feat};\n'
    return fea


SLOT_MARGIN = 15     # ink may reach this far past the slot's edges
FIT_WIDTH = 590      # a glyph narrowed to fit is this wide


def settle(name, style, contours, anchors):
    """An accented letter whose accent hangs off the slot (the horn of ơ, the caron of ď, the bars
    of Đ, Ł, Ħ) is moved back to the slot's centre if it fits, or else drawn whole and narrowed."""
    xs = [n[0] for c in contours for n in c]
    x0, x1 = min(xs), max(xs)
    if x0 >= -SLOT_MARGIN and x1 <= 600 + SLOT_MARGIN:
        return contours, anchors
    if x1 - x0 <= FIT_WIDTH:
        dx = round(300 - (x0 + x1) / 2)
        return ([[(x + dx, y, t) for x, y, t in c] for c in contours],
                {a: (x + dx, y) for a, (x, y) in anchors.items()})
    gl = G(name, style)
    gl.condense(FIT_WIDTH / S)
    return gl.final(), gl.placed


def ldot(contours, n, style):
    """ŀ: the source sets the middle dot close to its narrow l; here it keeps a gap of 70%
    of its own width from the stem, so it never touches in the heavier weights."""
    base, dots = contours[:n], contours[n:]
    xs = [p[0] for c in base for p in c]
    dx = [p[0] for c in dots for p in c]
    w = max(dx) - min(dx)
    target = (min(xs) + max(xs)) / 2 + STEM[style] * S / 2 + w * (0.7 + 0.5)
    shift = round(target - (min(dx) + max(dx)) / 2)
    return base + [[(x + shift, y, t) for x, y, t in c] for c in dots]

AFTER = {'ldot': ldot}


def make(name, style, done):
    """A glyph's finished contours, anchors and centre (in the cell's units)."""
    if name not in done:
        if name in STRUCTURE:
            base = make(STRUCTURE[name][0], style, done)
            contours, anchors = compose.assemble(name, style, STRUCTURE[name], base)
            if name in AFTER:
                contours = AFTER[name](contours, len(base[0]), style)
            contours, anchors = settle(name, style, contours, anchors)
        elif name in ALT:
            gl = G(ALT[name][0], style)
            ALT[name][1](gl)
            contours, anchors = gl.final(), gl.placed
        else:
            gl = G(SOURCE.get(name, name), style)
            R.get(name, default)(gl)
            contours, anchors = gl.final(), gl.placed
        xs = [n[0] for c in contours for n in c]
        done[name] = (contours, anchors, (min(xs) + max(xs)) / 2 if xs else 300)
    return done[name]


def master(style):
    f = ufoLib2.Font()
    i = f.info
    i.familyName, i.styleName = FAMILY, style
    i.unitsPerEm = 1000
    i.xHeight, i.capHeight = round(X_HEIGHT[style] * S), round(700 * S)
    i.ascender, i.descender = 800, -200
    i.openTypeHheaAscender, i.openTypeHheaDescender, i.openTypeHheaLineGap = 800, -200, 200
    i.openTypeOS2TypoAscender, i.openTypeOS2TypoDescender, i.openTypeOS2TypoLineGap = 800, -200, 200
    i.openTypeOS2WinAscent, i.openTypeOS2WinDescent = 900, 250
    i.openTypeOS2Selection = [7]
    i.postscriptIsFixedPitch = True
    i.openTypeOS2Panose = [2, 0, 5, 9, 0, 0, 0, 0, 0, 0]
    i.openTypeOS2WeightClass = WEIGHTS[style]
    i.versionMajor, i.versionMinor = 0, 101
    i.copyright = 'Copyright 2026 The Trupeer Sans Mono Project Authors. Drawn from Trupeer Sans (from Montagu Slab, copyright 2020 The Montagu Slab Project Authors).'
    i.openTypeNameLicense = 'This Font Software is licensed under the SIL Open Font License, Version 1.1.'
    i.openTypeNameLicenseURL = 'https://openfontlicense.org'

    order = ['.notdef']
    nd = f.newGlyph('.notdef'); nd.width = 600
    pp = nd.getPointPen()
    for pts in ([(60, 0), (540, 0), (540, 640), (60, 640)], [(100, 40), (100, 600), (500, 600), (500, 40)]):
        pp.beginPath()
        for p in pts: pp.addPoint(p, 'line')
        pp.endPath()
    done = {}
    for name in NAMES + list(ALT):
        contours, anchors, mid = make(name, style, done)
        dx = 0
        if name in MARKS:
            # combining accents take no room and sit over the character before them
            attach = next((a for a in sorted(anchors) if a.startswith('_')), None)
            dx = -300 - (anchors[attach][0] if attach else mid)
        ug = f.newGlyph(name)
        ug.width = 0 if name in MARKS else 600
        u = REG[name]['unicode'] if name in REG else None
        if u: ug.unicodes = [int(u, 16)]
        pp = ug.getPointPen()
        for c in contours:
            pp.beginPath()
            for x, y, t in c:
                pp.addPoint((x + dx, y), None if t == 'offcurve' else t)
            pp.endPath()
        for a, (x, y) in sorted(anchors.items()):
            ug.anchors.append(Anchor(round(x + dx), round(y), a))
        order.append(name)
    f.glyphOrder = order
    f.features.text = features()
    f.lib['public.openTypeCategories'] = {n: c for n, c in CATEGORIES.items() if n in f}
    return f


def main():
    os.makedirs(BUILD, exist_ok=True)
    doc = DesignSpaceDocument()
    ax = AxisDescriptor()
    ax.name, ax.tag, ax.minimum, ax.default, ax.maximum = 'Weight', 'wght', 100, 400, 700
    ax.map = AXIS_MAP
    doc.addAxis(ax)
    for style in MASTERS:
        path = os.path.join(BUILD, f'TrupeerSansMono-{style}.ufo')
        master(style).save(path, overwrite=True)
        s = SourceDescriptor()
        s.path, s.familyName, s.styleName = path, FAMILY, style
        s.location = {'Weight': MASTER_AT[style]}
        doc.addSource(s)
    for style, w in WEIGHTS.items():
        inst = InstanceDescriptor()
        inst.familyName, inst.styleName = FAMILY, style
        inst.location = {'Weight': dict(AXIS_MAP)[w]}
        inst.filename = f'instances/TrupeerSansMono-{style}.ufo'
        doc.addInstance(inst)
    ds = os.path.join(BUILD, 'TrupeerSansMono.designspace')
    doc.write(ds)

    fontmake = [sys.executable, '-m', 'fontmake', '-m', ds, '--overlaps-backend', 'pathops']
    subprocess.run(fontmake + ['-o', 'variable', '--output-path',
                               os.path.join(FONTS, 'variable', 'TrupeerSansMono[wght].ttf')], check=True)
    for fmt in ('ttf', 'otf'):
        subprocess.run(fontmake + ['-i', '-o', fmt, '--output-dir', os.path.join(FONTS, fmt)], check=True)


def preview():
    """Just the three masters as static fonts, for looking at: build/preview/."""
    from ufo2ft import compileTTF
    out = os.path.join(BUILD, 'preview')
    os.makedirs(out, exist_ok=True)
    for style in MASTERS:
        compileTTF(master(style), removeOverlaps=True, overlapsBackend='pathops').save(
            os.path.join(out, f'TrupeerSansMono-{style}.ttf'))
        print('built', style)


if __name__ == '__main__':
    preview() if '--preview' in sys.argv else main()
