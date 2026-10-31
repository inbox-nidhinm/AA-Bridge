"""Renders a sample sheet as a PNG: python specimen.py OUT.png

Lines are shaped with HarfBuzz (so stylistic sets work) and drawn with FreeType.
Needs uharfbuzz, freetype-py and Pillow."""
import os, sys
import freetype
import uharfbuzz as hb
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))     # the AA Bridge repo: sans-serif/, slab/, serif/
PREVIEW = os.path.join(HERE, 'build', 'preview')
MONO = {w: os.path.join(PREVIEW, f'AABridgeSansMono-{w}.ttf') for w in ('Thin', 'Regular', 'Bold')}
SANS = {w: os.path.join(REPO, 'sans-serif', 'fonts', 'ttf', f'AABridgeSans16pt-{w}.ttf') for w in ('Thin', 'Regular', 'Bold')}
SLAB_MONO = {w: os.path.join(REPO, 'slab', 'mono', 'fonts', 'ttf', f'AABridgeSlabMono-{w}.ttf')
             for w in ('Thin', 'Regular', 'Bold')}

INK, GREY, LABEL, ACCENT = (17, 17, 17), (150, 150, 150), (120, 120, 120), (229, 72, 77)
LABEL_FONT = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)

_faces, _hb = {}, {}


def draw_text(img, x, y, text, path, size, color=INK, features=None, colors=None):
    """Draw text with its baseline at y. colors: {index: colour} for single characters."""
    if path not in _faces:
        _faces[path] = freetype.Face(path)
        blob = hb.Blob.from_file_path(path)
        _hb[path] = hb.Font(hb.Face(blob))
    face, font = _faces[path], _hb[path]
    upem = face.units_per_EM
    face.set_char_size(int(size * 64))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {})
    k = size / upem
    pen = x
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        face.load_glyph(info.codepoint, freetype.FT_LOAD_DEFAULT | freetype.FT_LOAD_NO_HINTING)
        face.glyph.render(freetype.FT_RENDER_MODE_NORMAL)
        bm = face.glyph.bitmap
        if bm.width and bm.rows:
            mask = Image.frombytes('L', (bm.width, bm.rows), bytes(bm.buffer))
            gx = round(pen + pos.x_offset * k) + face.glyph.bitmap_left
            gy = round(y - pos.y_offset * k) - face.glyph.bitmap_top
            c = (colors or {}).get(info.cluster, color)
            img.paste(Image.new('RGB', mask.size, c), (gx, gy), mask)
        pen += pos.x_advance * k
    return pen


def label(img, x, y, text):
    ImageDraw.Draw(img).text((x, y), text, font=LABEL_FONT, fill=LABEL)


def sheet(out):
    W = 1800
    img = Image.new('RGB', (W, 2700), 'white')
    L = 40
    y = 30

    label(img, L, y, 'AA Bridge Sans Mono, Regular. The letters that change most to fill the slot, with their slots shown')
    y += 40
    size = 190
    text = 'iljrf1IJ'
    cell = 600 * size / 1000
    d = ImageDraw.Draw(img)
    for k in range(len(text)):
        d.rectangle([L + k * cell, y, L + (k + 1) * cell - 1, y + size * 1.0], outline=(225, 225, 225))
    draw_text(img, L, y + size * 0.8, text, MONO['Regular'], size)
    y += size * 1.0 + 20

    label(img, L, y, 'The same letters in AA Bridge Sans (grey) and AA Bridge Slab Mono, for reference')
    y += 40
    size = 120
    p = draw_text(img, L, y + size * 0.8, text, SANS['Regular'], size * 0.87, GREY)
    draw_text(img, p + 80, y + size * 0.8, text, SLAB_MONO['Regular'], size)
    y += size + 30

    label(img, L, y, 'AA Bridge Sans (grey, set at 87% so the x-heights match) above AA Bridge Sans Mono')
    y += 40
    size = 84
    for w in ('Thin', 'Regular', 'Bold'):
        draw_text(img, L, y + size * 0.8, 'Hamburgefonstiv agyrt QRS', SANS[w], size * 0.87, GREY)
        y += size * 1.0
        draw_text(img, L, y + size * 0.8, 'Hamburgefonstiv agyrt QRS', MONO[w], size)
        y += size * 1.15

    label(img, L, y, 'Thin, Regular and Bold')
    y += 36
    size = 58
    for w in ('Thin', 'Regular', 'Bold'):
        for line in ('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz 0123456789'):
            draw_text(img, L, y + size * 0.8, line, MONO[w], size)
            y += size * 1.12
        y += 10

    label(img, L, y, 'AA Bridge Sans Mono above AA Bridge Slab Mono: the same slot, x-height and capitals')
    y += 36
    size = 58
    for path in (MONO['Regular'], SLAB_MONO['Regular']):
        draw_text(img, L, y + size * 0.8, 'Illegal1 = O0o; minimum(will, fill)', path, size)
        y += size * 1.15

    label(img, L, y, 'Defaults: l and r with flags and feet. Below, the alternates: a curled-tail l (ss05) and a footless r (ss06)')
    y += 36
    size = 76
    line = 'll ill fill  rr err array'
    p = draw_text(img, L, y + size * 0.8, line, MONO['Regular'], size)
    y += size * 1.1
    draw_text(img, L, y + size * 0.8, line, MONO['Regular'], size, features={'ss05': True, 'ss06': True},
              colors={i: ACCENT for i, ch in enumerate(line) if ch in 'lr'})
    y += size * 1.2

    label(img, L, y, 'In code: Thin, Regular and Bold')
    y += 36
    size = 40
    code = [('Thin', 'def greet(name: str) -> str:'),
            ('Thin', '    return f"Hello, {name}!"  # 0O 1lI |'),
            ('Regular', 'const total = items.reduce((a, b) => a + b, 0);'),
            ('Regular', "if (x != y && z <= 42) { log('$%&@*#~^'); }"),
            ('Bold', 'SELECT id, name FROM users WHERE age > 21;')]
    for w, line in code:
        draw_text(img, L, y + size * 0.8, line, MONO[w], size)
        y += size * 1.25

    img.crop((0, 0, W, int(y + 30))).save(out)
    print('wrote', out, int(y + 30))


if __name__ == '__main__':
    sheet(sys.argv[1])
