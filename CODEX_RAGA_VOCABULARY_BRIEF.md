# CODEX BRIEF — the raga label vocabulary is capped, and the cap is throwing away real ragas

Written 2026-08-13 by the verifier seat. For the **outside-voice / GPT seat**.
This is an **audit**, not a refactor. Deliverable is a document plus one data
file. **Do not retrain anything, do not touch `identify_clip.py`, do not
download audio.**

## 0. The finding you are auditing

`normalize_ragas.py` collapses ~958 scraped raga spellings onto a canonical
vocabulary that is, by construction, **compmusic's 40 Carnatic ragas ∪ the
Saraga track-metadata raaga set**. Anything that does not pin to a hand alias or
fuzzy-match at cutoff 0.6 becomes `null` in `data/raga_aliases.json`.

274 of the 958 spellings map to `null`, covering **689 of 3,698** concert items
in `data/scraped_compositions.json` (18.6%).

The repo has treated that null bucket as junk. It is *documented as junk* —
memory and `HANDOFF_SESSION_0731.md` §9 both describe it as "junk keys → null".
That is only partly true. The bucket sorted by concert-item count opens:

```
36 Arabhi        28 darbAr       18 Vocal        16 dEvamanOhari
12 hamsanAdam    12 nAyaki       12 paras        11 AbhEri
11 keeravANi     11 Sivakavi     10 rEvati       10 kannaDagowLa
10 vAchaspati     9 valaji        8 jayamanOhari  8 mOhanakalyANi
 8 malayamArutam  8 navarasakannaDA  8 gowLipantu 8 rAmapriyA
```

Of the top 20, **17 are standard concert ragas** and three are junk (`Vocal`,
`Sivakavi`, an artist name). Ārabhi and Darbār alone are 64 items. `AbhEri` is
in there — and Ābhēri is exactly the raga that made `nagumomu ganaleni` a
mislabelled, unhittable clip in the frozen wild set (`data/RAGA_WILD_MEASUREMENT.md`,
corrected 2026-08-13).

So the hypothesis under audit is:

> **The raga model's ceiling is a vocabulary artifact, not a modelling limit.**
> Real ragas were discarded at the canonicalisation step because they were
> absent from a 40-name reference list, and every downstream count — corpus
> size, class count, field coverage — inherits that loss silently.

Your job is to establish how big the loss is, precisely, and to be adversarial
about the hypothesis rather than confirm it.

## 1. What to produce

### (a) `data/RAGA_VOCABULARY_AUDIT.md`

1. **Classify all 274 null keys** into exactly one of:
   - `raga` — a real Carnatic (or Hindustani-in-Carnatic-practice) raga name,
     with the canonical spelling it should map to;
   - `raga_variant` — a real raga name that is a spelling variant of a raga
     **already in the canonical vocabulary** and should have matched. These are
     outright bugs; call them that. (`Shankarabharana`, `Khamboji` and
     `Arabhi`/`Aarabhi` are three I already believe are in this class — verify,
     and find the rest.)
   - `junk` — dates, venues, artist names, instrument names, commentary
     (`Vocal`, `Incomplete`, `Music Academy`, `Click on the line`, …);
   - `ambiguous` — you genuinely cannot tell. Do not pad this bucket to be safe;
     say what evidence would settle each one.
2. **The cost, in items.** How many of the 689 concert items are behind each
   bucket. The `junk` share is the number that decides whether the repo's
   existing description was right.
3. **The cost, in classes.** Merge your recovered ragas with the existing cache
   inventory (`data/raga_v2_cache/{saraga_v3,archive_v3}/*.npz`, 88 ragas /
   1,297 tracks — count them yourself, do not take my number) and report how
   many *additional* classes would clear `min_tracks` at 10, 15, 20 and 25 **if
   the null items were correctly labelled and their audio fetched**. Be explicit
   that this is a ceiling: concert-programme items are not the same thing as
   downloadable audio, and you must say what fraction plausibly is.
4. **The adversarial section — argue the other side.** At minimum:
   - Are any of these nulls null *on purpose*? Check git history and comments on
     `normalize_ragas.py` before concluding a name was dropped by accident.
   - `_CANONICAL_ALIASES` exists precisely because difflib at 0.6 confuses
     genuinely different ragas (`saraswati`~`saramati` = 0.82,
     `hamsanadam`~`hamsanandi` = 0.80, both wrong). Recovering names by fuzzy
     matching risks **exactly that failure**, and a wrong merge is worse than a
     null because it silently poisons a class. Which of your recoveries are at
     risk? Name them.
   - Some entries are the *same raga under two names* (`AbhEri` /
     `karnATaka dEvagAndhAri` — the alias file already pins the compound
     spelling to the latter). Merging or splitting these changes class counts in
     both directions. Flag every such pair you find rather than deciding it.
   - Hindustani imports (`Bageshri`, `Jhinjoti`, `Khamaj`) — are these a real
     part of Carnatic concert repertoire, or scraping noise from mixed
     programmes?
5. **A recommendation with a cost.** Cheapest correct fix, what it buys, what it
   risks, and what it does *not* fix.

### (b) `data/raga_aliases_audit.json`

`{raw_spelling: {"bucket": "...", "canonical": "..." | null, "confidence":
"high"|"medium"|"low", "why": "..."}}` for all 274 null keys.

**Write this as a NEW file. Do not modify `data/raga_aliases.json`.** It is an
input to five committed measurements; changing it in place would invalidate
them. Whether it gets merged is Deepti's call, not yours and not mine.

## 2. Rules

- Deepti works in this repo from a separate terminal. **`git add <path>` only,
  never `git add -A`.** Branch is `probe/duration-and-negative-arm`.
- **Do not modify** `data/raga_aliases.json`, anything under `models/`,
  `identify_clip.py`, `normalize_ragas.py`, or anything under
  `data/raga_wild/` (frozen), `data/raga_audit/`, `data/raga_duration/`,
  `data/raga_domain/`.
- A parallel workhorse seat is running the `min_tracks` sweep and owns
  `scripts/raga_audit_levels.py`, `data/raga_coverage/` and
  `data/RAGA_COVERAGE_CURVE.md`. **Stay out of those paths.**
- State your confidence honestly. A `low` on a raga you are unsure of is worth
  more than a confident wrong merge — the whole point of this seat is that it
  does not take the other seat at face value.
- Append a dated entry to `AGENT_LOG.md` when done.

## 3. What would make this audit wrong

If the null bucket turns out to be mostly junk after all, say so plainly and
kill the hypothesis. The repo has retracted a headline number once already this
month (`data/QMAX_CONTAMINATION_AUDIT.md`, 60% → 9.5%) and that retraction was
the most valuable output of that week. A refuted hypothesis here is a good
result, not a failed job.
