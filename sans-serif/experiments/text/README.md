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

## Step 2: even strokes and plain letters (Regular only)

After step 1, Nidhin asked (2026-11-01) to thicken the thin strokes rather
than thin the thick ones, and for plainer letters. `step2.py` builds
`fonts/AABridgeSansTextStep2-Regular.ttf` from the current Regular (stem 104):

- thin strokes raised to 0.89 of the stem (was 0.61), including the thin top of C and G
- no curls or balls: a, c, f (fi, fl), g, 6, Q, j
- R with a straight leg ending just inside the bowl; S as one smooth even stroke
- longer E middle bar; r's arm end as thick as the stem; smaller i/j dots (all 29 letters with that dot)
- outlines merged, no overlaps

It reads darker than Before and Inter (like a Medium); a lighter base is an
option if that is too heavy. `plot.py` draws outlines on a grid for planning.

## Step 3: one stroke width (Regular only)

Nidhin's notes (2026-11-01): strokes the same width in every letter, varying
only slightly at joints; t without its curved foot; single-storey g as the
default; plain a, c, f. `step3.py` redraws a-z, A-Z, 0-9, fi and fl from centre
lines with one pen (`--weight`, default 100), keeping each letter's current
width, height and stem positions (t and f narrower). Every measured stroke is
1.00 of the pen. Accented letters get the new base letter; everything not
redrawn goes through step 2's even-stroke pass. Builds
`fonts/AABridgeSansTextStep3-Regular.ttf`.

Step 1's C75/C82/C88 were set aside after this (still in this folder).

## Next steps

1. Decide the weight of the text Regular (pen width).
2. Narrow round letters and figures; shorten t, f and r; plain t.
3. Distinct I and l; tabular figures.
4. Respace and re-kern by eye.
5. Draw the text cut into the source as its own masters, all weights; extend opsz down to about 10 or 12.
