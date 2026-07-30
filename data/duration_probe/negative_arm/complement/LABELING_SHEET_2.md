# Negative-arm labeling sheet 2 — the half you have not heard

**51 rows, one label each. One file to listen to per row.**

## Why there is a second sheet

Sheet 1 played 10s every 20s of each 300s window: 0-10s, 20-30s, and so on. That is half the window. The other half — 15 stretches of 10s each, including the final 10s — was never played to anyone.

For most questions that would be fine. For this one it is not: a single sung line hiding in an unheard gap is enough to make the matcher answer, and this arm exists precisely to count how often it answers when it should not. So the rows you already called `no-sahitya` need their other half checked before they can be used.

Each `_scan2.wav` below is exactly that missing half — 150s, the snippets sheet 1 skipped, in order. Together the two sheets cover every second of the window with nothing heard twice.

## The question is unchanged

**Does anyone sing words?** Not which composition, not whether we have it — those are lookups.

**Stop as soon as you hear singing.** Write `sahitya` and move on; you do not have to finish the sweep. Most rows should end in seconds.

**You can stop anywhere in the sheet.** Blank rows are unknown and excluded, and the order is freshly shuffled, so a partial sheet is a valid smaller experiment rather than a broken one.

| label | means |
|---|---|
| `no-sahitya` | nobody sings words anywhere in the sweep: alapana, tanam, thani, swaram, tuning, applause, speech, instrumental |
| `sahitya` | somebody sings words somewhere in it, even one line, even briefly |
| `unusable` | you cannot tell — too noisy, too broken, genuinely ambiguous |

`unusable` and blank both count as **unknown** and are excluded; neither is treated as no-sahitya. Guessing costs us more than abstaining does.

**An item is used only if BOTH sheets say `no-sahitya`.** A `sahitya` here overrides sheet 1 — it means the window does contain singing, and sheet 1 simply did not play the part that held it. Expect this sheet to shrink the usable set; that is the point of running it.

If a row is borderline, the full 300s window is on disk as `../../negatives/<id>d300.wav` — but only open it if the sweep is genuinely ambiguous.

Ids are blind and the order is reshuffled with a new seed, so the row order tells you nothing about your sheet-1 answers (`METRIC_CONTRACT.md:30`).

| # | listen | label | notes |
|---:|---|---|---|
| 1 | `neg047_scan2.wav` | no-sahitya |  |
| 2 | `neg002_scan2.wav` | no-sahitya |  |
| 3 | `neg005_scan2.wav` | no-sahitya |  |
| 4 | `neg007_scan2.wav` | no-sahitya |  |
| 5 | `neg035_scan2.wav` | no-sahitya |  |
| 6 | `neg063_scan2.wav` | no-sahitya |  |
| 7 | `neg069_scan2.wav` | no-sahitya |  |
| 8 | `neg004_scan2.wav` | no-sahitya |  |
| 9 | `neg064_scan2.wav` | no-sahitya |  |
| 10 | `neg038_scan2.wav` | no-sahitya |  |
| 11 | `neg041_scan2.wav` | no-sahitya |  |
| 12 | `neg048_scan2.wav` | no-sahitya |  |
| 13 | `neg012_scan2.wav` | no-sahitya |  |
| 14 | `neg067_scan2.wav` | no-sahitya |  |
| 15 | `neg045_scan2.wav` | no-sahitya |  |
| 16 | `neg053_scan2.wav` | sahitya |  |
| 17 | `neg008_scan2.wav` | no-sahitya |  |
| 18 | `neg034_scan2.wav` | no-sahitya |  |
| 19 | `neg054_scan2.wav` | no-sahitya |  |
| 20 | `neg049_scan2.wav` | no-sahitya |  |
| 21 | `neg011_scan2.wav` | no-sahitya |  |
| 22 | `neg068_scan2.wav` | no-sahitya |  |
| 23 | `neg020_scan2.wav` | sahitya | has some swara and lyrics |
| 24 | `neg000_scan2.wav` | no-sahitya | pretty noisy |
| 25 | `neg024_scan2.wav` | no-sahitya |  |
| 26 | `neg043_scan2.wav` | no-sahitya |  |
| 27 | `neg003_scan2.wav` | no-sahitya |  |
| 28 | `neg032_scan2.wav` | no-sahitya |  |
| 29 | `neg065_scan2.wav` | no-sahitya |  |
| 30 | `neg001_scan2.wav` | no-sahitya |  |
| 31 | `neg026_scan2.wav` | no-sahitya |  |
| 32 | `neg052_scan2.wav` | no-sahitya |  |
| 33 | `neg017_scan2.wav` | no-sahitya |  |
| 34 | `neg029_scan2.wav` | no-sahitya |  |
| 35 | `neg046_scan2.wav` | no-sahitya |  |
| 36 | `neg025_scan2.wav` | no-sahitya |  |
| 37 | `neg039_scan2.wav` | no-sahitya |  |
| 38 | `neg010_scan2.wav` | no-sahitya |  |
| 39 | `neg044_scan2.wav` | no-sahitya |  |
| 40 | `neg021_scan2.wav` | no-sahitya |  |
| 41 | `neg018_scan2.wav` | no-sahitya |  |
| 42 | `neg055_scan2.wav` | no-sahitya |  |
| 43 | `neg014_scan2.wav` | no-sahitya |  |
| 44 | `neg019_scan2.wav` | no-sahitya |  |
| 45 | `neg022_scan2.wav` | no-sahitya |  |
| 46 | `neg016_scan2.wav` | no-sahitya |  |
| 47 | `neg061_scan2.wav` | no-sahitya |  |
| 48 | `neg033_scan2.wav` | no-sahitya |  |
| 49 | `neg040_scan2.wav` | no-sahitya |  |
| 50 | `neg060_scan2.wav` | no-sahitya |  |
| 51 | `neg036_scan2.wav` | no-sahitya |  |
