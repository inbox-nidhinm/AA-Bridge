"""Proof images for the text cut test fonts.

usage (from the repo root): python sans-serif/experiments/text/proof.py
Needs hb-view (HarfBuzz) on the PATH. Writes PNGs to experiments/text/proofs/.
"""
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
OUT = os.path.join(HERE, 'proofs')
INTER = os.path.expanduser('~/Library/Fonts/Inter-Regular.ttf')
os.makedirs(OUT, exist_ok=True)

SETS = [('Before', os.path.join(FONTS, 'AABridgeSansTextBefore-Regular.ttf')),
        ('C75', os.path.join(FONTS, 'AABridgeSansTextC75-Regular.ttf')),
        ('C82', os.path.join(FONTS, 'AABridgeSansTextC82-Regular.ttf')),
        ('C88', os.path.join(FONTS, 'AABridgeSansTextC88-Regular.ttf')),
        ('Step2', os.path.join(FONTS, 'AABridgeSansTextStep2-Regular.ttf')),
        ('Step3', os.path.join(FONTS, 'AABridgeSansTextStep3-Regular.ttf')),
        ('Inter', INTER)]

LETTERS = 'Hamburgefonstiv acfgtrvy RQSG 0126'
PARA = ('Screen typography is judged at small sizes, in long\n'
        'paragraphs, under poor light. The letters have to stay\n'
        'distinct when each stroke is a pixel or two wide, and the\n'
        'texture has to stay even so the eye can move along the line.')


def hb(font, text, size, path, line_space=0):
    subprocess.run(['hb-view', f'--font-file={font}', f'--font-size={size}', '--margin=10',
                    f'--line-space={line_space}', '-o', path, text], check=True)
    return Image.open(path).convert('L')


def stack(images, labels, path, scale=1):
    lab = ImageFont.truetype('/System/Library/Fonts/SFNSMono.ttf', 13)
    w = max(i.width for i in images) + 80
    h = sum(i.height for i in images) + 8 * len(images)
    sheet = Image.new('L', (w, h), 255)
    d = ImageDraw.Draw(sheet)
    y = 0
    for im, t in zip(images, labels):
        sheet.paste(im, (80, y))
        d.text((6, y + 12), t, font=lab, fill=110)
        y += im.height + 8
    if scale != 1:
        sheet = sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
    sheet.save(path)


tmp = os.path.join(OUT, '_part.png')
LET = [s for s in SETS if s[0] in ('Before', 'Step2', 'Step3')]
big = [hb(f, LETTERS, 120, tmp) for _, f in LET]
stack(big, [s for s, _ in LET], os.path.join(OUT, 'letters.png'))
for size in (13, 16):
    PS = [s for s in SETS if s[0] in ('Before', 'Step3', 'Inter')]
    paras = [hb(f, PARA, size, tmp, size // 2) for _, f in PS]
    stack(paras, [s for s, _ in PS], os.path.join(OUT, f'paragraph-{size}px.png'), scale=2)
os.remove(tmp)
print('wrote', sorted(os.listdir(OUT)))
