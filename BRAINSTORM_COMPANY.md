# Carnatify company/robustness brainstorm

2026-07-11. Response to HANDOFF_CLIP_ID.md §7. Grounded in scoreboard facts:
lyrics path 6/8 top-5 on wild clips; melody dead on clips; ASR ceiling is the
binding constraint; tonic unsolved; 10-clip test set is the only real eval.

## 0. One-line strategy

Product = **canonical composition registry + rendition/query graph**, not the
models. Models are replaceable; verified Carnatic data at wild-clip quality
does not exist anywhere else. Every design choice below feeds that asset.

## 1. Data moat (develop the seed)

- **Canonical composition table**: stable composition ID, composer, raga,
  tala, language, alias list (spelling variants, script variants). Sources to
  merge: lyrics.db titles, qmax catalog titles, karnatik/shivkumar-style
  lyrics sites, blog tracklists. This directly fixes handoff §6.4 (half of
  rank-1 errors = title-collision noise) — hygiene work and moat work are the
  SAME work.
- **Pallavi-line index**: most 60s wild clips capture pallavi (repeated most).
  Index compositions by first-line/pallavi phonetic key, not whole-lyric bag.
  Matcher already rewards repetition — formalize: pallavi tokens weighted up.
- **Rendition graph**: composition → many renditions (artist, era, source,
  quality tier). Cross-rendition variety is exactly what melody path lacked;
  collecting it now keeps contrastive-embedding option alive later.
- **Human verification queue**: Deepti (later: musician volunteers) approves
  auto-ingested labels. "Verified by musicians" badge = trust moat big players
  can't fake. Track verifier per row from day one.
- **Ingestion legality**: archive.org + sangeethapriya OK-ish; YouTube needs
  permission; user uploads need explicit consent checkbox + license text.
  Cheap to do now, expensive to retrofit.

## 2. User-in-the-loop labeling (the flywheel)

- Every confirmed query = labeled wild clip = exactly the starved data class.
  Store (with consent): audio hash + audio, ASR transcript, features, top-5
  shown, which one user picked, or "none of these".
- Confirmed clips flow into: (a) wild-clip regression suite growth,
  (b) per-source calibration training (see §4), (c) future contrastive
  embedding corpus, (d) new-alias discovery (user picks title spelled
  differently than transcript).
- "Not in catalog — add it?" flow: user supplies title/raga, lands in
  verification queue. Misses become catalog growth instead of churn.
- Cold start: Deepti's teacher network, student WhatsApp groups, sabha
  volunteers. 50 users confirming 5 clips/week = 250 labeled wild clips/week
  — dwarfs anything recordable solo.

## 3. Segmented pipeline (cheap, big robustness win)

Clip-type classifier BEFORE matching. Features nearly free:
- ASR token density + vowel ratio: alapana = akaara, near-zero consonant
  tokens. Whisper already runs; classifier is a byproduct.
- Percussion/vocal energy split (demucs stems or spectral flux): thani
  avartanam = percussion-dominant.
- Voicing fraction from existing pyin/melodia output: instrumental detection.

Routes: kriti → lyrics path; alapana → raga-only answer with honest framing
("no lyrics in this section — raga guess: X"); thani → "percussion solo, tala
info only / try another section"; instrumental kriti → melody path (weak) +
"point at a sung section" prompt. Wrong-tool-for-clip errors disappear from
the scoreboard.

## 4. Hybrid retrieval done right

- ONE canonical composition index. Sources = lyrics token score, raga
  posterior, (full-recording only) Qmax. Each source emits calibrated
  log-odds; calibration fit on user-confirmed clips, NOT internal CV
  (handoff lesson: same-corpus calibration lies).
- Raga as FILTER not adder: raga posterior top-8 shrinks candidate set before
  lyrics scoring — avoids the proba-blending trap already proven harmful
  (§5.3-4). Filter with escape hatch: if lyrics score is very high outside
  raga top-8, trust lyrics (raga model is the weaker voter on wild clips).
- Abstention is a first-class output. Below threshold → "sing a cleaner
  pallavi" instead of a wrong top-5. Never bluff.

## 5. ASR leverage beyond handoff §6.2

(§6.2 list — IndicWhisper, large-v3 on Colab, demucs-before-whisper, VAD
chunking — still first. Additions:)
- **Catalog-biased decoding**: whisper `initial_prompt` seeded with high-prior
  catalog vocabulary (composer names, common sahitya words). Zero cost, often
  worth points on proper nouns.
- **N-best union**: sample whisper at 2-3 temperatures, union tokens. Matcher
  is coverage-based — recall-oriented transcripts help, precision noise mostly
  washes out.
- **Script normalization layer**: whisper emits Latin/Devanagari/Tamil
  inconsistently. Fold everything to one phonetic key (ISO 15919-ish, vowel
  squash) before matching — same fold as ground-truth matching (§8 gotcha).
- **Rescore, don't trust**: treat transcript as noisy channel; match catalog
  n-grams against it fuzzily (already partly done via token coverage) —
  future: match against whisper segment-level alternatives, not final string.
- **faster-whisper int8** (ctranslate2): 4-8x speedup claim → turns HF-space
  60s clip from ~30-60s to ~10s. Latency AND cost lever. Test accuracy delta
  on the 10 clips first.

## 6. Eval culture → CI

- `test_sung_clips/` + manifest = regression suite. One command prints the
  scoreboard table (top-1/top-5 per clip type). Run on every matcher/model
  change; diff vs last committed scoreboard; regression blocks ship.
- Grow to 30-50 clips (Deepti recordings) stratified by: era, gender,
  recording quality, clip type, language. Track per-stratum numbers — 6/8
  aggregate hides failure modes.
- Rule already in handoff, worth engraving: no same-corpus benchmark ever
  green-lights a ship again.

## 7. Product wedges (company angle)

- **Why Shazam/SoundHound can't just do this**: fingerprinting matches exact
  recordings; Carnatic value is live/new renditions of known compositions —
  composition-level ID across renditions. Their architecture is the wrong
  shape; our data + niche verification is defensible.
- **Concert-companion mode**: continuous listening, item-boundary detection,
  live setlist with lyrics+meaning per item. Killer demo for rasikas AND a
  data-collection machine (every concert = many segments).
- **Student mode**: sing/hum → "you're singing X in raga Y", lyrics + meaning
  + notation link. HS/music-school market Deepti knows personally.
- **Distribution**: music schools + sabhas as partners — they supply
  verification labor and users; app supplies lyrics/meaning value. Community
  before monetization; freemium later (meaning/notation depth, companion
  mode).

## 8. Sequencing (moat-aware version of handoff §6)

1. Ship lyrics-first `identify_clip.py` + top-5 confidence UX (handoff §6.1).
2. Canonical composition table + alias merge (§6.4 — also moat step 1).
3. ASR sprint on the 10 clips (§6.2 + §5 above); regression suite growth in
   parallel (§6.3).
4. Deploy with confirm-button feedback loop from day one (§2 above — do NOT
   ship v1 without it; every early user query is irreplaceable data).
5. Clip-type router (§3 above).
6. Calibrated hybrid retrieval once confirmations accumulate (§4 above).
