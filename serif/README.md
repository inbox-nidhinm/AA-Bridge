# AA Bridge Serif and AA Bridge Serif Wedge

Two serif families made from AA Bridge Slab's own drawings by one script. Spacing and kerning are the Slab's, unchanged (apart from the Wedge's J, below).

- **AA Bridge Serif** (this folder): bracketed serifs, with beaks and spurs redrawn to match.
- **AA Bridge Serif Wedge** (`wedge/`): small straight-sided wedge serifs, the same on both sides of every stem and shorter on slanted stems. Beaks and spurs stand square to the grid (vertical outer edge, small flat tip), and the spurs of C, G and S widen into the bowl. Four letters are redrawn to lose the Slab's traits: G (wedge ends on the bar, a pointed spur cut diagonally at the foot), J (descends below the baseline into a round hook with a vertical cut, and is narrower, so its top-left serif sits where I's does), R (a straight diagonal leg with wedge feet) and S (beaks at both terminals).

Seven weights, Thin to Bold, in display and 16pt optical sizes, plus a variable font with both axes.

## Rebuilding

The serif sources are generated, never edited by hand, so they stay in step with the Slab. After a change to `../slab/sources/AABridgeSlab.glyphs`:

```
python tools/serifize.py ../slab/sources/AABridgeSlab.glyphs sources/AABridgeSerif.glyphs
python tools/serifize.py ../slab/sources/AABridgeSlab.glyphs sources/AABridgeSerifWedge.glyphs --style wedge
```

then build the fonts with fontmake (`-o variable otf ttf -i`). To change the look, edit the ratios at the top of `tools/serifize.py` (bracketed: `T_RATIO`, `BRACKET`, `BEAK_T`; wedge: `W_REACH` and `W_ASPECT` for the size of the wedges, `W_HDROP` for lowercase heads, `WB_TIP` and `WB_IN` for beaks, `WS_BASE` and `WS_SLOPE` for spurs, `W_SLANT` for slanted stems). Wedge-only changes never touch the bracketed output; check it stays byte-identical.

## License

SIL Open Font License 1.1, as for AA Bridge Slab (see `OFL.txt`).
