# Title resolution — rebuild audit

Generated 2026-07-28 by `scripts/duration_probe_titles.py`, published because
`HANDOFF_SESSION_0728.md` §7.2 requires the false-merge audit on the record
before any relaxed matching is used.

Reproduce with: `venv_train/bin/python scripts/duration_probe_titles.py`

---

## 1. What was wrong

`CODEX_NEGATIVE_ARM_REVIEW.md` §2 established that `NUM_PREFIX` stripped only
**1-3** leading digits, so seven-digit Jamendo ids survived into the title
(`1224830 aswinsainarain.mp3` → `4830 aswinsainarain`). Registry lookup on such
a string fails for reasons having nothing to do with the recording, and the old
negative arm then declared the item out-of-catalog. At least 3 of the 12
nominal OOC items were in-catalog works.

## 2. What changed

- Any number of leading digits is stripped, including archive track ranges
  (`29-30 72_...`).
- The authoritative title is `file_title_raw` in
  `data/concert_audio/download_manifest.json` **when the filename is
  demonstrably not a title** — a stripped four-plus-digit id, a generic archive
  slot name (`Track 02`, `Concert 163`, `A`, `xxxx`), or too short. The
  filename otherwise wins, because the corpus's own downloader already produced
  a cleaned title for 1,222 of 1,238 files and the raw string usually carries
  the raga and composer too.
- A section name can no longer resolve to a work. `Alapana.mp3` previously
  matched `comp00196` (canonical "Alapana", 19 ragas, no lyrics — already on
  the reviewed junk blocklist) and `rAgam tAnam pallavi.mp3` matched
  `comp06030`. **`comp06030` "Ragam Thanam Pallavi" is NOT yet on
  `data/registry_junk_blocklist.json` and should be looked at** — it is a
  section name the live matcher can return as a composition.

Title provenance across all 1,238 files:

| provenance | files |
|---|---:|
| `filename` | 1222 |
| `manifest_segment` | 8 |
| `manifest_raw` | 5 |
| `filename_unrecoverable` | 3 |

## 3. Effect on the recall pool — **zero**

```
=== POOL CONSTRUCTION (distinct title keys: 923) ===
  matched_but_no_lyrics            505
  RESOLVED                         271
  too_short                        117
  no_registry_match                 30
resolved pool: 271 titles
  5 carry a work-family id set (>1 registry row)
  100 distinct archive clusters (118 unknown)
```

Delta against the pre-registered counts (`distinct 922 / 505 / 271 / 117 / 29`):
distinct title keys +1, `matched_but_no_lyrics` 0, **`RESOLVED` 0**,
`too_short` 0, `no_registry_match` +1. Not one title entered or left the pool,
and the reported delta is stated rather than assumed, as §7.1 required.

The keys did move. Twelve id-mangled keys disappeared and thirteen real titles
appeared in their place — `alaipayutey`, `cinnancirukiliye`,
`santanagopalakrisnam`, `cinnancirupennpole`, `irakkam`, `muralidara`,
`kanadavarnam`, `varnamvasanta` and others. All of them land in
`no_registry_match`, which is the point: they are the contaminated OOC
candidates, and they are now legible enough for the relaxed key to disqualify.

## 4. Relaxed key — what it is and where it may be used

`cskel()` drops vowels, unifies voicing (`d/t`, `b/p`, `g/k`, `j/c`), unifies
nasal place (`m/n`), and collapses gemination, over the top of the live
matcher's own `skey`. Matching allows an edit distance of 1 on that skeleton.

**It may only ever disqualify.** `resolve_relaxed()` is used to remove an item
from the OOC stratum; it is never allowed to create a truth id. Over-matching
therefore costs sample size and never validity. The only sanctioned non-exact
route into truth is the hand-reviewed
`data/duration_probe/title_aliases.json`, which is currently empty.

### Calibration — the three cases the review proved were contaminated

| filename title | exact `skey` | relaxed | resolves to | review said |
|---|---|---|---|---|
| `santanagopalakrishnam` | miss | HIT | `comp06603` | comp06603 |
| `alaipayuthey` | miss | HIT | `comp00183` | comp00183 |
| `chinnanchiru kiliye` | miss | HIT | `comp01145`, `comp01147` | comp01145 |

All three, on the ids the review named.

### False-merge audit

| measure | value |
|---|---:|
| registry names indexed | 9653 |
| distinct skeletons | 8301 |
| skeletons actually consulted (length ≥ 4) | 8058 |
| skeletons covering more than one registry id | 388 |
| registry ids touched by a collision | 910 |
| short skeletons never consulted | 243 |
| names already colliding under exact `skey` | 0 |

So ~4.8% of the consulted skeleton space is ambiguous, touching 910 of 8,688
registry rows. Worst collisions are short skeletons where a title is almost all
vowels — `ntntn` (11 ids), `ntnt` (11), `nrkn` (7), `nvnt` (7). Every one of
these makes the OOC filter **stricter**: an item colliding with anything is
excluded from the OOC stratum. That is the safe error direction, and it is why
the key is confined to exclusion.

## 5. Effect on the negative arm — decisive

Of 1,238 recordings: 1,175 resolve exactly, 16 resolve only under the relaxed
key, 36 are free-form sections, 11 resolve to nothing at all.

The 16 relaxed-only matches include every item the review flagged, plus the
seven `melakartalecdems` lecture-demonstration tracks, `mangalam`,
`tOm tOm tadhara` and `muralidhara`. Under the old exact-only rule all 16 were
eligible to be counted as OOC negatives.

### The 16, published with a verdict each (added 2026-07-29)

Round 2 of the review asked for these to be written down rather than left
implied. Regenerated from the live resolver, not from recollection.

| filename title | relaxed match(es) | verdict |
|---|---|---|
| `alaipayuthey` | comp00183 `alai pAyudE` | **TRUE** — transliteration variance only; the review named this id |
| `chinnanchiru-kiliye` | comp01145 `chinnam ciru kiLiyE`, comp01147 `cinnanjiru kiLiyE` (+comp00146) | **TRUE** for the two `kiLiyE` rows, which are each other's work-family; comp00146 `A Gopala Adhitama` is a false third |
| `muralidhara` | comp04369, comp04425, comp04447 | **PLAUSIBLE, unresolvable** — comp04446/47 `muraLIdhara …` are real candidates, but a bare first word cannot pick between them |
| `B - Harikambhoji` | comp04463 `muruganai bhaji` | **FALSE** — a raga name colliding with an unrelated kriti under vowel-dropping |
| `Dhirasankarabaranam-Naganandini` | comp06602 `santAna gOpala` | **FALSE** — two raga names, unrelated work |
| `nI nAma rUpamulaku nitya` | comp03917 `mA kulamuna`, comp04951 `nee kElana` | **FALSE** — and the most informative one: a genuine sahitya line with **no** registry row (searched: no `nAma rUpamula*` row exists) collided with two unrelated works |
| `mangalam` | comp03917, comp04951 | **FALSE** — a closing-item genre, not a work |
| `tOm tOm tadhara` | comp01230, comp01401, comp01678 | **FALSE** — tanam syllables, not a composition |
| `Melakartha Chakkaram` + 7 raga-suffixed variants (`Mayamalavagaula`, `Sarasangi`, `Simhendramadhayama`, `Ganamurti`, `Lathangi`, `Kantamani`, `Syamalangi`) | 3-id sets, heavily repeated | **FALSE** — lecture-demonstration tracks. The skeleton is degenerate here: eight distinct titles collapse onto only four id-sets, and `Mayamalavagaula`, `Melakartha Chakkaram` and `Syamalangi` return the *same* three ids |

Tally: **2 true** (3 ids), **1 plausible but unresolvable**, **13 false**.

**Why this is documentation and not a bug.** The relaxed key may only
disqualify, so each false match costs one OOC candidate and never corrupts a
truth label — the error direction is safe by construction. But it is now
measured rather than asserted, and it carries a completeness caveat that should
be stated wherever the empty OOC stratum is quoted: **relaxed matching
establishes the specificity of the retained OOC cases, not the absence of OOC
audio.** Short and vowel-heavy genuine OOC titles are exactly what this key
over-matches, so they are systematically the ones it would silently exclude.
`nI nAma rUpamulaku nitya` is the worked example — a real sung line with no
registry row, excluded from the OOC stratum by a collision with two works it
has nothing to do with.

The 11 survivors are `G C-8-13781 13162o`, `HMV P 5866 G C -8-10152`,
`Melakartha Chakkaram`, `B - Karaharapriya`, `A - Saveri`,
`IMCpresents-In-Memoriam-...`, `SSI`, `xxxx`, `varnam vasantha`, `SN 501`,
`G C-8-13782 13163o`. **Not one of them names a composition.** They are upload
ids, shellac catalogue numbers, archive slot names, and a genre paired with a
raga.

Conclusion, recorded in `data/duration_probe/verified_ooc.json`: the OOC
stratum is empty, and not because sampling failed. This corpus cannot supply
out-of-catalog truth — its registry was partly built from these filenames.
Measuring OOC abstention at 300s needs prospectively acquired audio.
