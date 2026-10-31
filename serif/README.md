# AA Bridge Serif and AA Bridge Serif Wedge

Two serif families made from AA Bridge Slab's own drawings by one script. Spacing and kerning are the Slab's, unchanged.

- **AA Bridge Serif** (this folder): bracketed serifs, with beaks and spurs redrawn to match.
- **AA Bridge Serif Wedge** (`wedge/`): wedge serifs. They get relatively shorter at heavier weights and on slanted stems, so Bold counters stay open.

Seven weights, Thin to Bold, in display and 16pt optical sizes, plus a variable font with both axes.

## Rebuilding

The serif sources are generated, never edited by hand, so they stay in step with the Slab. After a change to `../slab/sources/AABridgeSlab.glyphs`:

```
python tools/serifize.py ../slab/sources/AABridgeSlab.glyphs sources/AABridgeSerif.glyphs
python tools/serifize.py ../slab/sources/AABridgeSlab.glyphs sources/AABridgeSerifWedge.glyphs --style wedge
```

then build the fonts with fontmake (`-o variable otf ttf -i`). To change the look, edit the ratios at the top of `tools/serifize.py` (bracketed: `T_RATIO`, `BRACKET`, `BEAK_T`; wedge: `W_H`, `W_H_BOLD`, `W_SLANT`).

## License

SIL Open Font License 1.1, as for AA Bridge Slab (see `OFL.txt`).
