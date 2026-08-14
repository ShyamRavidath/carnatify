# Raga equivalence decisions — Deepti's rulings, 2026-08-13

**Status: RECORDED, NOT APPLIED.** Nothing in this file has been acted on. No
alias map, model, tier, or measurement has been changed because of it. Deepti
asked explicitly that these be written down and left alone for now.

The questions come from `data/RAGA_VOCABULARY_AUDIT.md` §"Same/close names that
change counts", where the outside-voice seat flagged four name pairs it refused
to decide because each changes class counts in both directions and the call is a
musician's, not a model's.

Deepti is a practising Carnatic musician. Her ruling is the ground truth here,
the same way her label audit became ground truth for the 29 wild clips.

---

## 1. Ābhēri / Karṇāṭaka dēvagāndhāri — **technically distinct, practically inseparable**

> "technically distinct, but they are known to be very similar nowadays, a
> nuance that will be near-impossible to distinguish."

**Ruling: they are two ragas, and this model should not be asked to tell them
apart.**

This is a *more useful* answer than a merge or a split, because it says the
distinction is real in theory and unavailable in practice from audio. The
consequences, none of them applied yet:

- Do **not** claim a Karṇāṭaka dēvagāndhāri capability separate from Ābhēri.
- The two are candidates for a **single merged training class** on engineering
  grounds — not because they are the same raga, but because the boundary is not
  learnable and a model forced to split them will spend its confidence on a
  coin flip. If merged, the merged class must be **labelled honestly to the
  user**, e.g. "Ābhēri (also heard as Karṇāṭaka dēvagāndhāri)", never as a
  confident single name.
- Counting effect if merged: 13 programme items + 8 cache tracks. The audit
  says the merge adds **one class at `min>=15` and at `min>=20`**, and none at
  `min>=10` or `min>=25`.
- This is the pair behind Deepti's own wild-set correction #2 (`nagumomu
  ganaleni`), and behind the live `'AbEri' -> 'Sāvēri'` wrong merge in
  `data/raga_aliases.json`. **The Sāvēri merge is wrong under any reading of
  this ruling and should be fixed regardless of what is decided here.**

## 2. Bhīmpalās — **yes, the same; it is the Hindustani version**

> "yes it is, it is just the hindustanti version."

**Ruling: Bhīmpalās is the Hindustani counterpart of (modern) Ābhēri.**

Consequences, not applied:

- +8 programme items join the Ābhēri group. The audit's arithmetic: Ābhēri +
  Karṇāṭaka dēvagāndhāri + Bhīmpalās reaches **29 items, which clears
  `min>=25`**.
- Caveat the audit raised and this ruling does not settle: scale equivalence is
  not identical grammar, and a Hindustani rendition may differ in gamaka,
  phrase shape and typical tempo from a Carnatic one even at the same scale.
  Deepti's answer is about **raga identity**, which is what was asked. Whether
  the two make one good *training class* is an empirical question that a
  held-out test can answer and this ruling does not.

## 3. Durgā / Śuddha Sāvēri — **not the same**

> "yea they r not the same."

**Ruling: keep separate. Do not merge.**

This confirms the audit's own recommendation ("Do not auto-merge; phrases
differ") and, together with §1, shows the two calls are being made on musical
grounds rather than as a blanket policy — one pair is inseparable in practice,
another is genuinely distinct.

Counting effect: none. Neither crosses a threshold either way.

## 4. Udayaravicandrika / Śuddhadhanyāsi — **NOT ANSWERED**

Four pairs were put to Deepti; three answers came back. Her third answer is read
here as applying to Durgā / Śuddha Sāvēri, which was the third pair listed and
the one the audit had explicitly recommended against merging.

**This pair is therefore still open.** It has no threshold consequence
(1 + 15 items, no class crosses a boundary at any tier), so nothing is blocked
by it. Ask when convenient; do not guess.

The audit's own position, for whoever asks: follow the explicit parenthetical in
the source metadata at medium confidence, noting that schools differ.

---

## Also still awaiting Deepti, from the same audit

Not asked yet, listed so they are not lost:

- **Nine low-confidence `raga` rows** and **one low-confidence `raga_variant`**
  in `data/raga_aliases_audit.json` — filter on `"confidence": "low"`.
- **Two `ambiguous` rows** the outside-voice seat refused to classify.
- **Hindustani imports as a product policy question**, not a musical one: the
  null bucket holds 31 such items (Bhīmpalās 8, Durgā 6, Gauḍ Malhār 3,
  Jhinjhōṭi 3, Candrakauns 2, Pīlū 2, Pūrvī 2, Pūriyā 2, and one each of
  Dīpāli, Hindustāni Kāpi, Miśra Yaman). All arrive from Carnatic-vocal concert
  pages attached to Carnatic artists, so they are repertoire, not scraping
  noise. The question is whether "concert companion" covers every item on a
  programme or only core elaborated Carnatic ragas.

## What needs no ruling and should be fixed anyway — **DONE 2026-08-13**

The eight **live wrong merges** in `data/raga_aliases.json`, verified by the
verifier seat:

```
'AbEri'             -> 'Sāvēri'              'gaulipantu'      -> 'Gauḷa'
'garuDwani'         -> 'Kāmavardani'         'jayantasri'      -> 'Dhanaśrī'
'sunAdavinOdhini'   -> 'Jaganmōhini'         'nalainakAnti'    -> 'Kalāvati'
'navarasas kannaDa' -> 'Bṛndāvana sāranga'   'veera vasanatam' -> 'Vasanta'
```

These are not equivalence questions; they are mistakes.

**Repaired 2026-08-13**, after the tier work was decided
(`data/RAGA_TIER_GRADUATION.md`), in a commit of its own with regression tests
at `tests/test_raga_aliases.py` (23 tests). All ten keys now resolve to `null`.

**Why this needed no musical adjudication, and why that is checkable.** For nine
of the ten, **the alias map already contained the right answer under a different
spelling of the same name.** `'AbhEri'`, `'Abheri'` and `'abheri'` all mapped to
`null`; only `'AbEri'` mapped to `'Sāvēri'`. Same for `sunAdavinOdhini` against
four null siblings, `nalainakAnti` against three, `veera vasanatam` against four,
`jayantasri` against `jayantasree`, `garuDwani` against `garuDadwani`, and both
`navarasa` spellings against two. The repair was not a judgment about what Ābhēri
is — it was making one key agree with its own siblings. That invariant is what
the tests encode, so a future scrape or a difflib match at the 0.6 cutoff cannot
re-introduce any of them silently.

`gaulipantu -> Gauḷa` is the single entry with no sibling in the map. It rests on
the plain fact that Gaulipantu is not Gauḷa.

**Eight aliases turned out to be ten keys.** `garuDwani`/`garudwani` are one
alias in two cases. And the repair itself found a tenth: **`'navasrasa kannaDA'
-> 'Bṛndāvana sāranga'`**, sitting two lines below its twin in the file, carrying
the identical wrong target with the same unanimous null siblings. It was fixed on
exactly the same mechanical evidence and is named here rather than slipped in.

**Downstream effect, measured and negligible.** 20 programme items rode the ten
keys (the "17" above counted the eight). If `raga_canonical` is regenerated,
3,009 labelled items become 2,989 and 54-class repertoire coverage moves
**79.196% → 79.224%**, expected hits 46.86 → 46.88. **The tier decision is not
disturbed.** `data/scraped_compositions.json` has deliberately **not** been
regenerated — the map and the materialised field currently disagree by these 20
items, and re-deriving is a separate dated step whose only effect is the +0.02
above.

### Still flagged, deliberately not repaired

**`'garuDadhwani' -> 'Śuddadhanyāsi'`.** Garuḍadhvani is a janya of
Śankarābharaṇaṁ; Śuddhadhanyāsi is pentatonic. This looks like the same class of
mistake, and its sibling `garuDadwani` is `null`. It was **not** repaired,
because unlike `navasrasa kannaDA` it is not a typo of a name the map already
resolves to `null` — it asserts a specific and *different* raga, so repairing it
is a musical claim rather than a bookkeeping one, and the verifier seat's
verified list excluded it. `tests/test_raga_aliases.py` pins its current value so
the question cannot be closed silently in either direction. **Ask Deepti.**
