"""Cut a test font from a Regular build: only the key letters (and space),
renamed so it installs next to AA Bridge Slab without clashing.

usage: testfont.py BUILD.otf OUT.otf [FAMILY]
"""
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

KEY = 'HORSAandglovesxpy '


def main():
    src, out = sys.argv[1], sys.argv[2]
    family = sys.argv[3] if len(sys.argv) > 3 else 'AA Bridge Slab Tall Test'
    font = TTFont(src)
    opts = subset.Options()
    opts.layout_features = ['*']
    opts.name_IDs = ['*']
    s = subset.Subsetter(opts)
    s.populate(text=KEY)
    s.subset(font)
    ps = family.replace(' ', '') + '-Regular'
    names = {1: family, 3: f'{ps};experiment', 4: f'{family} Regular', 6: ps, 16: family, 17: 'Regular'}
    for rec in list(font['name'].names):
        if rec.nameID in names:
            rec.string = names[rec.nameID]
    if 'CFF ' in font:
        cff = font['CFF '].cff
        cff.fontNames = [ps]
        top = cff.topDictIndex[0]
        top.FullName, top.FamilyName = f'{family} Regular', family
    font.save(out)
    print(out, len(font.getGlyphOrder()), 'glyphs')


if __name__ == '__main__':
    main()
