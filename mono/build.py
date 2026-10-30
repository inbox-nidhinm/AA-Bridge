"""Builds Trupeer Slab Mono, Thin to Bold: python build.py

Draws the Thin, Regular and Bold masters into build/ as UFOs with a designspace, then
makes the variable font (fonts/variable) and seven static weights (fonts/ttf, fonts/otf)."""
import os, subprocess, sys
import ufoLib2
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor
from tools import G, REG, S, MASTERS
from recipes import R, SOURCE, default

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
FONTS = os.path.join(HERE, 'fonts')
FAMILY = 'Trupeer Slab Mono'

# The original's weight axis: user value -> where the drawings sit (its Regular is drawn at 378)
AXIS_MAP = [(100, 100), (200, 180), (300, 260), (400, 378), (500, 492), (600, 588), (700, 700)]
WEIGHTS = {'Thin': 100, 'ExtraLight': 200, 'Light': 300, 'Regular': 400, 'Medium': 500, 'SemiBold': 600, 'Bold': 700}
MASTER_AT = {'Thin': 100, 'Regular': 378, 'Bold': 700}
X_HEIGHT = {'Thin': 517, 'Regular': 528, 'Bold': 539}


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
    i.versionMajor, i.versionMinor = 0, 300
    i.copyright = 'Copyright 2026 The Trupeer Slab Mono Project Authors. Drawn from Trupeer Slab (Montagu Slab, copyright 2020 The Montagu Slab Project Authors).'
    i.openTypeNameLicense = 'This Font Software is licensed under the SIL Open Font License, Version 1.1.'
    i.openTypeNameLicenseURL = 'https://openfontlicense.org'

    order = ['.notdef', 'space']
    nd = f.newGlyph('.notdef'); nd.width = 600
    pp = nd.getPointPen()
    for pts in ([(60, 0), (540, 0), (540, 640), (60, 640)], [(100, 40), (100, 600), (500, 600), (500, 40)]):
        pp.beginPath()
        for p in pts: pp.addPoint(p, 'line')
        pp.endPath()
    sp = f.newGlyph('space'); sp.width = 600; sp.unicodes = [0x20]

    for name, g in REG.items():
        u = g['unicode']
        if not u or not (0x21 <= int(u, 16) <= 0x7E): continue
        gl = G(SOURCE.get(name, name), style)
        R.get(name, default)(gl)
        ug = f.newGlyph(name); ug.width = 600; ug.unicodes = [int(u, 16)]
        pp = ug.getPointPen()
        for c in gl.final():
            pp.beginPath()
            for x, y, t in c:
                pp.addPoint((x, y), None if t == 'offcurve' else t)
            pp.endPath()
        order.append(name)
    f.glyphOrder = order
    return f


def main():
    os.makedirs(BUILD, exist_ok=True)
    doc = DesignSpaceDocument()
    ax = AxisDescriptor()
    ax.name, ax.tag, ax.minimum, ax.default, ax.maximum = 'Weight', 'wght', 100, 400, 700
    ax.map = AXIS_MAP
    doc.addAxis(ax)
    for style in MASTERS:
        path = os.path.join(BUILD, f'TrupeerSlabMono-{style}.ufo')
        master(style).save(path, overwrite=True)
        s = SourceDescriptor()
        s.path, s.familyName, s.styleName = path, FAMILY, style
        s.location = {'Weight': MASTER_AT[style]}
        doc.addSource(s)
    for style, w in WEIGHTS.items():
        inst = InstanceDescriptor()
        inst.familyName, inst.styleName = FAMILY, style
        inst.location = {'Weight': dict(AXIS_MAP)[w]}
        inst.filename = f'instances/TrupeerSlabMono-{style}.ufo'
        doc.addInstance(inst)
    ds = os.path.join(BUILD, 'TrupeerSlabMono.designspace')
    doc.write(ds)

    fontmake = [sys.executable, '-m', 'fontmake', '-m', ds, '--overlaps-backend', 'pathops']
    subprocess.run(fontmake + ['-o', 'variable', '--output-path',
                               os.path.join(FONTS, 'variable', 'TrupeerSlabMono[wght].ttf')], check=True)
    for fmt in ('ttf', 'otf'):
        subprocess.run(fontmake + ['-i', '-o', fmt, '--output-dir', os.path.join(FONTS, fmt)], check=True)


main()
