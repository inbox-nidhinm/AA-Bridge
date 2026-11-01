"""Set AA Bridge Sans's version in the built fonts without rebuilding them.

usage (from the repo root):
    python sans-serif/tools/setversion.py 0.106

Rewrites head.fontRevision, the version string (name ID 5), the version inside
the unique ID (name ID 3) and the CFF version of every file in
sans-serif/fonts (otf, ttf, variable, webfonts). Outlines, metrics and features
are untouched. The source's versionMajor/versionMinor are set to match, so the
next fontmake build carries the same number.

Version numbers are written the font way: v0.1.6 is 0.106, as 1.006 was v1.0.6.
"""
import glob
import os
import re
import sys

from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
new = sys.argv[1]
major, minor = new.split('.')
rev = float(new)

paths = []
for sub in ('otf', 'ttf', 'variable', 'webfonts'):
    paths += sorted(glob.glob(os.path.join(ROOT, 'fonts', sub, '*.*')))

for p in paths:
    f = TTFont(p)
    old = f['name'].getDebugName(5)
    f['head'].fontRevision = rev
    for rec in f['name'].names:
        s = rec.toUnicode()
        if rec.nameID == 5:
            rec.string = re.sub(r'^Version \d+\.\d+', f'Version {new}', s)
        elif rec.nameID == 3:
            rec.string = re.sub(r'^\d+\.\d+', new, s)
    if 'CFF ' in f:
        top = f['CFF '].cff.topDictIndex[0]
        if hasattr(top, 'version'):
            top.version = new
    f.save(p)
    print(f'{os.path.relpath(p, ROOT)}: {old} -> {TTFont(p)["name"].getDebugName(5)}')

src = os.path.join(ROOT, 'sources', 'AABridgeSans.glyphs')
text = open(src).read()
text = re.sub(r'versionMajor = \d+;', f'versionMajor = {int(major)};', text)
text = re.sub(r'versionMinor = \d+;', f'versionMinor = {int(minor)};', text)
open(src, 'w').write(text)
print('source:', re.findall(r'version(?:Major|Minor) = \d+;', text))
