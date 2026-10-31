# AA Bridge Sans Text (experiment)

A text cut for AA Bridge Sans, made for screens at 12 to 16px. The display cut
(opsz 144) stays as it is. This folder is a proofing area: nothing here changes
the released fonts.

The audit that started this found that at text sizes the Sans has too much
stroke contrast, a heavy and wide Regular, curled display terminals, overly
wide t f r, look-alike I and l, no tabular figures and formula spacing.

## Step 1: contrast and weight (Regular only)

Stem brought down from 104 to 90 units; thin strokes brought up in three
versions:

| Regular, text size | Before | C75 | C82 | C88 | Inter |
|---|---|---|---|---|---|
| n stem | 104 | 90 | 90 | 90 | 84 |
| Top of o | 63 | 68 | 74 | 79 | 75 |
| Thin ÷ stem | 0.61 | 0.76 | 0.82 | 0.88 | 0.90 |
| x-height | 528 | 530 | 532 | 534 | 545 |

C82 is the suggested level. Widths, terminals and everything else are unchanged.

- `textcut.py` builds the test fonts into `fonts/` (method and rebuild notes in its docstring)
- `check.py` measures strokes; `check.py --sweep AABridgeSansTextC82-Regular.ttf` flags any stroke darker than the stem
- `proof.py` writes PNG proofs into `proofs/` (needs `hb-view`)

Run them from the repo root with a Python that has fontTools and Pillow.

## Next steps

1. Narrow round letters and figures; shorten t, f and r.
2. Plain terminals for a c f t 5 6 g R Q (curls stay in the display cut).
3. Distinct I and l; tabular figures.
4. Respace and re-kern by eye.
5. Draw the text cut into the source as its own masters, all weights; extend opsz down to about 10 or 12.
