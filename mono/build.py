"""Builds Trupeer Slab Mono Regular into fonts/ (and the UFO into build/): python build.py"""
import sys, os
import ufoLib2, ufo2ft
from tools import G, REG, S
from recipes import R, SOURCE

HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, 'fonts')
os.makedirs(out, exist_ok=True)
os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
f = ufoLib2.Font()
i = f.info
i.familyName, i.styleName = 'Trupeer Slab Mono', 'Regular'
i.unitsPerEm = 1000
i.xHeight, i.capHeight = round(528 * S), round(700 * S)
i.ascender, i.descender = 800, -200
i.openTypeHheaAscender, i.openTypeHheaDescender, i.openTypeHheaLineGap = 800, -200, 200
i.openTypeOS2TypoAscender, i.openTypeOS2TypoDescender, i.openTypeOS2TypoLineGap = 800, -200, 200
i.openTypeOS2WinAscent, i.openTypeOS2WinDescent = 900, 250
i.openTypeOS2Selection = [7]
i.postscriptIsFixedPitch = True
i.openTypeOS2Panose = [2, 0, 5, 9, 0, 0, 0, 0, 0, 0]
i.openTypeOS2WeightClass = 400
i.versionMajor, i.versionMinor = 0, 200
i.copyright = 'Copyright 2026 The Trupeer Slab Mono Project Authors. Drawn from Trupeer Slab (Montagu Slab, copyright 2020 The Montagu Slab Project Authors).'
i.openTypeNameLicense = 'This Font Software is licensed under the SIL Open Font License, Version 1.1.'
i.openTypeNameLicenseURL = 'https://openfontlicense.org'

order = ['.notdef', 'space']
nd = f.newGlyph('.notdef'); nd.width = 600
pp = nd.getPointPen()
for box in ((60, 0, 540, 640), (100, 40, 500, 600)):
    x0, y0, x1, y1 = box
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)] if box[0] == 60 else [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
    pp.beginPath()
    for p in pts: pp.addPoint(p, 'line')
    pp.endPath()
sp = f.newGlyph('space'); sp.width = 600; sp.unicodes = [0x20]

for name, g in REG.items():
    u = g['unicode']
    if not u or not (0x21 <= int(u, 16) <= 0x7E): continue
    gl = G(SOURCE.get(name, name))
    if name in R: R[name](gl)
    ug = f.newGlyph(name); ug.width = 600; ug.unicodes = [int(u, 16)]
    pp = ug.getPointPen()
    for c in gl.final():
        pp.beginPath()
        for x, y, t in c:
            pp.addPoint((x, y), None if t == 'offcurve' else t)
        pp.endPath()
    order.append(name)
f.glyphOrder = order
f.save(os.path.join(HERE, 'build', 'TrupeerSlabMono-Regular.ufo'), overwrite=True)
tt = ufo2ft.compileTTF(f, removeOverlaps=True)
tt.save(os.path.join(out, 'TrupeerSlabMono-Regular.ttf'))
ot = ufo2ft.compileOTF(f, removeOverlaps=True)
ot.save(os.path.join(out, 'TrupeerSlabMono-Regular.otf'))
print('glyphs', len(order))
