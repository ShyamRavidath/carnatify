# The 11 long-form concerts

Deepti's own recordings of live Carnatic concerts, converted to mp3 on
2026-08-13 by `scripts/convert_long_concerts.sh` (44.1 kHz stereo 192 kbps —
the same audio regime as `data/concert_audio`, so nothing downstream sees a new
one). **9.85 hours over 11 concerts, 851 MB.**

`handoff.md` §5.1: **this is the only unmeasured cell in the entire product
case.** Every wild clip previously on disk is 43-85 s. The concert-companion
thesis rests on 10-30 minute items, and the duration curve says that region is
68.8-71.0% on *clean* audio and has never been tested on *wild* audio.

## State

| step | status |
|---|---|
| converted to mp3 | done 2026-08-13 (10 converted, 0 failed) |
| given a home in the repo | done — `data/long_concerts/audio/`, gitignored |
| **frozen** | **done — `FROZEN_CONCERTS.json`, committed before any prediction exists** |
| labelled by Deepti | **pending — `LABELS.tsv`, see below** |
| scoring preregistration | pending; written once the tier decision and the labels are both settled |
| scored | pending |

## The freeze

`FROZEN_CONCERTS.json` records, per file: sha256, byte length, ffprobe duration,
codec, sample rate, channels, bit rate, and the sha256 of the copy still in
`~/Downloads` — all eleven are byte-identical to their Downloads copy, and the
durations reproduce `handoff.md` §5.1's table exactly.

It is committed **before any prediction exists**, so a later score cannot
quietly be computed on a re-encoded or substituted file. This is the discipline
`data/raga_wild/FROZEN_CLIPS.json` used and it is the reason that measurement is
trustworthy. Re-verify at any time, and before scoring:

```
venv_train/bin/python scripts/long_concert_freeze.py --verify
```

It exits non-zero on any mismatch and never edits the frozen record.

## What is needed from Deepti

**Fill in `LABELS.tsv`.**

**Each of these recordings contains MANY songs, so each concert gets MANY rows.**
One row per song: which concert, when it starts, what raga. The song ends where
the next row starts, so no end times are ever typed.

The file already lays out blank rows under each concert heading — **7 to 20 of
them, scaled by the concert's length** — so there is somewhere to type. Add more
rows if a concert has more songs than there are blanks; leftover blanks are
ignored completely and cost nothing.

```
concert         start   raga            item                confidence  notes
long_concert_1  0:00    Nata            jagadanandakaraka   high
long_concert_1  9:20    Kalyani         alapana + nidhi     high        long alapana
long_concert_1  31:05   ragamalika      viruttam            medium      excluded
long_concert_1  38:40   Sindhubhairavi  thillana            low         noisy, unsure
```

Four rows, one concert. The second song runs 9:20 → 31:05 because the next row
starts there.

**A song you are unsure about is not a problem — write `unsure` or `ragamalika`
and it is excluded rather than counted wrong.** Guessing is the only thing that
would damage the measurement. Likewise, doing three concerts properly is worth
more than eleven done vaguely: a concert with no ragas filled in is dropped, not
guessed at.

```
venv_train/bin/python scripts/long_concert_labels.py --validate
```

checks the file and prints what it found. It never edits `LABELS.tsv`. It
reports, separately and without ever summing them:

- items excluded because they are `ragamalika` or `unsure` — written as such,
  they are dropped rather than counted wrong;
- items whose raga **is** in the corpus vocabulary (scorable);
- items whose raga is **not** — these are not errors, they are the
  out-of-vocabulary rate, which is the quantity `data/RAGA_CEILING_EVALUATION.md`
  says is the binding product constraint. Measuring it on real concerts Deepti
  attended is worth as much as the accuracy number.

Partial is fine and useful. A concert with no ragas filled in is dropped, not
guessed at. Only `high` confidence rows go in the primary read-out; `medium` and
`low` are reported beside it and never merged in.

The `item` and `notes` columns are never scored — they are there so the results
table is readable afterwards.

## Deliberately not done yet

**No preregistration, no scoring harness, no prediction.** The scoring prereg
fixes the model, the tier, the windowing and the read-outs, and it will be
committed as its own commit before the harness exists — house standard. Two
things have to settle first: the raga tier decision (`handoff.md` §5.2, which
changes the class count the concerts would be scored against) and the labels.

Writing the prereg before either is settled would either register a model that
is about to be replaced or register the windowing after seeing the item lengths.

## Notes

- The audio lives in `audio/` and is **gitignored** (851 MB). The freeze record,
  the labels, the scripts and the write-ups are tracked.
- The `~/Downloads` copies are byte-identical and therefore redundant. Deleting
  them, and the 8.1 GB of `.mp4`/`.MOV` sources, is **Deepti's call**
  (`handoff.md` §6.2) — the conversion script never deletes a source and neither
  does anything here.
- **Do not move these into `~/sung_tests`.** That is the short-clip wild set and
  its composition is load-bearing for six committed measurements.
