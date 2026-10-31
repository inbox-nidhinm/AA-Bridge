# AA Bridge

Six type families from one source, sorted by classification. All of them grew out of Montagu Slab (copyright 2020 The Montagu Slab Project Authors) and are released under the SIL Open Font License 1.1 (see the `OFL.txt` in each folder).

| Folder | Family | What it is | Weights |
| --- | --- | --- | --- |
| `slab/` | AA Bridge Slab | The original slab serif, with display and 16pt optical sizes | Thin to Bold, variable `opsz` + `wght` |
| `slab/mono/` | AA Bridge Slab Mono | Monospaced companion to AA Bridge Slab | Thin to Bold, variable `wght` |
| `sans-serif/` | AA Bridge Sans | The slabs taken off AA Bridge Slab | Thin to Bold, variable `opsz` + `wght` |
| `sans-serif/mono/` | AA Bridge Sans Mono | Monospaced companion to AA Bridge Sans | Thin to Bold, variable `wght` |
| `serif/` | AA Bridge Serif | Bracketed serifs, generated from AA Bridge Slab | Thin to Bold, variable `opsz` + `wght` |
| `serif/wedge/` | AA Bridge Serif Wedge | Wedge serifs, generated from AA Bridge Slab | Thin to Bold, variable `opsz` + `wght` |

Each family folder has the same layout:

- `fonts/otf/` and `fonts/ttf/`: static fonts. Files with `16pt` in the name are the text size; the others are the display size.
- `fonts/variable/`: one file holding every weight (and, where there is one, every optical size).
- `fonts/webfonts/`: the variable font as WOFF2, for websites.
- `sources/`: the Glyphs source files. The monos are built from their parent's source by the scripts in their folder (`python build.py`), and the serifs by `serif/tools/serifize.py` (see `serif/README.md`).

## History

This repo joins what used to be three: Trupeer Slab (with Trupeer Slab Mono), Trupeer Sans (with Trupeer Sans Mono) and Trupeer Serif (bracketed and Wedge), renamed AA Bridge on 2026-10-31. The Slab and Sans commits are kept in full; `git log` shows them as the two merged branches near the start.
