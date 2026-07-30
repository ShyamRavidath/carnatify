# Negative-arm labeling sheet — duration probe (rebuilt 2026-07-28)

**70 rows, one label each. One file to listen to per row.**

Each `_scan.wav` is a 10s-every-20s sweep of the exact 300s window the pipeline will be given — about 150s of listening, covering half of it with no unheard gap longer than 10s. Last time you were given three 20s excerpts from elsewhere in the recording; five of them turned out not to overlap the scored window at all, which is why this is a sweep of the window itself.

**The only question is whether anyone sings words.** Not which composition, not whether we have it — those are lookups, and asking your ear for them was my mistake last round.

**Stop as soon as you hear singing.** The moment anyone sings words, write `sahitya` and go to the next row — you do not have to finish the sweep. Most rows should end in a few seconds; only the genuinely lyric-free ones cost you the full sweep.

**You can stop anywhere in the sheet.** Rows you leave blank are treated as unknown and excluded, and the order is random, so a partial sheet is a valid smaller experiment rather than a broken one. More labeled rows buys tolerance for a bad item: ~40 confirmed no-sahitya rows survive one surprise answer, ~55 survive two.

| label | means |
|---|---|
| `no-sahitya` | nobody sings words anywhere in the sweep: alapana, tanam, thani, swaram, tuning, applause, speech, instrumental |
| `sahitya` | somebody sings words somewhere in it, even one line, even briefly |
| `unusable` | you cannot tell — too noisy, too broken, genuinely ambiguous |

`unusable` and blank both count as **unknown** and are excluded; neither is treated as no-sahitya. Guessing costs us more than abstaining does.

If a row is borderline, the full 300s window is on disk as `../negatives/<id>d300.wav` — but only open it if the sweep is genuinely ambiguous.

Ids are blind and the order is shuffled, so the filenames tell you nothing (`METRIC_CONTRACT.md:30`).

| # | listen | label | notes |
|---:|---|---|---|
| 1 | `neg014_scan.wav` | no-sahitya |  |
| 2 | `neg000_scan.wav` | no-sahitya |  |
| 3 | `neg067_scan.wav` | no-sahitya |  |
| 4 | `neg035_scan.wav` | no-sahitya |  |
| 5 | `neg047_scan.wav` | no-sahitya |  |
| 6 | `neg052_scan.wav` | no-sahitya |  |
| 7 | `neg031_scan.wav` | sahitya |  |
| 8 | `neg056_scan.wav` | sahitya | lyrics are stretched, so its a little hard to identify |
| 9 | `neg018_scan.wav` | no-sahitya |  |
| 10 | `neg002_scan.wav` | no-sahitya |  |
| 11 | `neg003_scan.wav` | no-sahitya | violin audio |
| 12 | `neg061_scan.wav` | no-sahitya |  |
| 13 | `neg016_scan.wav` | no-sahitya |  |
| 14 | `neg042_scan.wav` | sahitya |  |
| 15 | `neg059_scan.wav` | sahitya |  |
| 16 | `neg064_scan.wav` | no-sahitya |  |
| 17 | `neg054_scan.wav` | no-sahitya |  |
| 18 | `neg006_scan.wav` | sahitya | towards end song starts |
| 19 | `neg066_scan.wav` | sahitya |  |
| 20 | `neg069_scan.wav` | no-sahitya |  |
| 21 | `neg036_scan.wav` | no-sahitya |  |
| 22 | `neg065_scan.wav` | no-sahitya |  |
| 23 | `neg021_scan.wav` | no-sahitya |  |
| 24 | `neg017_scan.wav` | no-sahitya |  |
| 25 | `neg029_scan.wav` | no-sahitya |  |
| 26 | `neg039_scan.wav` | no-sahitya |  |
| 27 | `neg024_scan.wav` | no-sahitya |  |
| 28 | `neg041_scan.wav` | no-sahitya |  |
| 29 | `neg060_scan.wav` | no-sahitya |  |
| 30 | `neg007_scan.wav` | no-sahitya | slightly noisy |
| 31 | `neg037_scan.wav` | sahitya | might be a RTP, hard to tell |
| 32 | `neg045_scan.wav` | no-sahitya |  |
| 33 | `neg032_scan.wav` | no-sahitya |  |
| 34 | `neg050_scan.wav` | sahitya | pretty noisy |
| 35 | `neg034_scan.wav` | no-sahitya |  |
| 36 | `neg022_scan.wav` | no-sahitya |  |
| 37 | `neg040_scan.wav` | no-sahitya |  |
| 38 | `neg038_scan.wav` | no-sahitya |  |
| 39 | `neg019_scan.wav` | no-sahitya | emcee mostly |
| 40 | `neg057_scan.wav` | sahitya |  |
| 41 | `neg012_scan.wav` | no-sahitya |  |
| 42 | `neg062_scan.wav` |  |  |
| 43 | `neg063_scan.wav` | no-sahitya |  |
| 44 | `neg023_scan.wav` | sahitya |  |
| 45 | `neg025_scan.wav` | no-sahitya |  |
| 46 | `neg033_scan.wav` | no-sahitya |  |
| 47 | `neg068_scan.wav` | no-sahitya |  |
| 48 | `neg020_scan.wav` | no-sahitya |  |
| 49 | `neg001_scan.wav` | no-sahitya  | flute audio |
| 50 | `neg009_scan.wav` | sahitya |  |
| 51 | `neg049_scan.wav` | no-sahitya |  |
| 52 | `neg043_scan.wav` | no-sahitya |  |
| 53 | `neg015_scan.wav` | sahitya |  |
| 54 | `neg008_scan.wav` | no-sahitya | end is tanam |
| 55 | `neg026_scan.wav` | no-sahitya |  |
| 56 | `neg013_scan.wav` | sahitya |  |
| 57 | `neg028_scan.wav` | sahitya | Pretty sure this is a RTP |
| 58 | `neg010_scan.wav` | no-sahitya |  |
| 59 | `neg048_scan.wav` | no-sahitya |  |
| 60 | `neg051_scan.wav` | sahitya |  |
| 61 | `neg053_scan.wav` | no-sahitya |  |
| 62 | `neg044_scan.wav` | no-sahitya |  |
| 63 | `neg005_scan.wav` | no-sahitya | veena audio |
| 64 | `neg055_scan.wav` | no-sahitya |  |
| 65 | `neg011_scan.wav` | no-sahitya |  |
| 66 | `neg058_scan.wav` | sahitya | might be an RTP |
| 67 | `neg027_scan.wav` | unusable |  |
| 68 | `neg004_scan.wav` | no-sahitya | *clarification -- this is tanam, so it has some characters but no actual sahitya |
| 69 | `neg030_scan.wav` | sahitya | has swara in it |
| 70 | `neg046_scan.wav` | no-sahitya |  |
