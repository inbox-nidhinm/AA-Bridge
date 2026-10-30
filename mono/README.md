# Trupeer Slab Mono

A monospaced companion to Trupeer Slab. Every character takes the same 600-unit slot.

Only the Regular exists so far: the 95 basic keyboard characters, in `fonts/` as TTF and OTF.

![The original Trupeer Slab in grey above Trupeer Slab Mono, then lines of code](specimen.png)

## How it is made

The glyphs are the original's own Regular drawings (the 16pt optical size in `../sources/TrupeerSlab.glyphs`), not new ones.

- **Scale.** The original is set at 87% in the slot (`S` in `tools.py`). At that size its n fits the slot as drawn, which is how typewriter slab monospaces like Courier keep natural proportions: a smaller x-height, not narrower letters. Most lowercase, the figures and most punctuation are used unchanged, only centred.
- **Narrow letters** (i, l, j, r, f, t, I, J, 1) get longer slabs, bars and arms to fill the slot.
- **Wide letters** (most capitals, m, w, &, @, %) get narrower counters and serifs. Their stems keep their weight: x is moved towards the original's Bold drawing before narrowing (`G.condense`). m, w, M and W are kept slightly lighter so they don't read as dark blots.
- **M** keeps upright legs with the V's point raised, as in Courier and IBM Plex Mono.
- **For code:** the original's slashed zero is the default 0, ' and " are straight wedges, / and \ run from below the baseline to above the capitals, and the underscore fills the slot.

Each change is a recipe in `recipes.py`. A glyph without a recipe is used as drawn.

## Building

```bash
pip install -r requirements.txt
python build.py
```

This writes `fonts/TrupeerSlabMono-Regular.ttf` and `.otf`, and the UFO into `build/`.

## Licence

SIL Open Font License 1.1, as for Trupeer Slab (see `../OFL.txt`).
