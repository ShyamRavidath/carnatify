# PRD: Carnatify

**Document version:** 1.0  
**Status:** Approved for development  
**Owner:** Deepti  
**Last updated:** June 2026  

---

## 1. Executive Summary

Carnatify is a Carnatic music identification and enrichment app built by a practicing Carnatic musician, for the Carnatic music community. It does two independent things: (1) identifies which composition is being performed from live or recorded audio — tolerant of different artists, tempos, and improvisation, unlike exact-fingerprint approaches like Shazam — and (2) classifies the raga and tala being performed, which works even on improvised passages where no fixed composition exists. Both features feed a single display: composition name, composer, raga, tala, original-language lyrics (sahityam), and an English meaning.

The project is driven by a gap that the builder has experienced personally: sitting in a Carnatic concert and not knowing which kriti is being sung, not knowing its meaning, and having no tool that could help. Every existing tool either identifies ragas as a static reference (you look up a raga by name) or fails completely on live, artist-specific, gamaka-heavy renditions. Carnatify is the tool that should exist for concert-goers and students of the tradition.

The MVP is a Python research pipeline that proves the ML core works. A native iOS app is the explicit next phase. The eventual target is an App Store release for the Carnatic music community globally.

---

## 2. Problem Statement

Carnatic classical music is a rich, living tradition with thousands of compositions spanning multiple composers and languages. Yet for a concert-goer, a student, or even a practicing musician encountering an unfamiliar performance, there is no tool that can:

1. Identify *which specific composition* is being performed live, despite the fact that every artist renders it differently — different tempo, different shruti (tonic), extensive improvisation, and ornamental variation (gamakas) that fundamentally changes the acoustic signal.
2. Identify the *raga* and *tala* being performed — especially important during improvisational sections (alapana, kalpana swaram) that have no fixed "composition" to match against.
3. Surface the *sahityam* (lyrics) and *meaning* of the composition immediately, in the listener's preferred language.

Existing tools fail because:
- **Shazam / audio fingerprinting**: matches a specific recording acoustically, fails completely on live performance or any rendition different from the stored reference.
- **Raga reference apps** (e.g. "Carnatic Raga" on App Store): static lookup tools — you search a raga by name; they don't listen to anything.
- **General music recognition apps**: built on Western harmonic/chordal analysis (chroma features) that benchmark poorly on monophonic, gamaka-heavy Carnatic melody.

The gap is not a niche edge case. It is the default experience for anyone attending a Carnatic concert who isn't already a seasoned performer with deep repertoire knowledge.

---

## 3. Goals & Objectives

### Primary goals
- **G1:** Build a composition identification feature that correctly identifies ≥ 70% of known compositions in a held-out test set, despite variation in artist, tempo, and shruti.
- **G2:** Build a raga classification feature that achieves ≥ 75% accuracy across the ragas covered in the Saraga + Saraga Audiovisual datasets (~60+ ragas).
- **G3:** Build a tala detection module that correctly identifies the rhythmic cycle (tala) being performed.
- **G4:** Surface correct original-language lyrics and coherent English meaning for matched compositions.
- **G5:** Deliver a working Python MVP that can take audio input and return all of the above in a usable interface.

### Secondary goals
- **G6:** Structure the codebase so that the ML core (feature extraction, classifiers, matching engine) is modular and portable — the iOS app layer wraps it, not rebuilds it.
- **G7:** Build the lyrics + meaning catalog broadly from day one, independent of audio ML progress.

### Non-goals
- Real-time word-level synced lyrics (forced alignment is a separate research problem; deferred)
- Raga identification for the full theoretical universe of ragas (bounded by available labeled data)
- Identification of compositions outside the reference catalog (~100–150 pieces for composition matching MVP)
- Native iOS app (explicitly deferred to phase 2)
- Hindustani music support (Carnatic only for MVP)

---

## 4. User Personas

### Persona 1 — The Builder + Primary User (primary)
**Name:** Deepti  
**Background:** Practicing Carnatic musician, high school student with strong CS/ML background. Has personal experience of the problem (wanting to identify unfamiliar compositions at concerts). Plans App Store release for the broader Carnatic community.  
**Goal:** Build a tool she actually wants to use herself, that works well enough for a live demo and is structured correctly for an eventual iOS release.  
**Frustration:** Tools that sort of work on easy cases and completely fail on the live, improvised, artist-variable audio that actually occurs at concerts.

### Persona 2 — The Concert-Goer (secondary, future user)
**Profile:** Attendee at a Carnatic kutcheri (concert), ranging from experienced community members to younger listeners or newcomers. May know some ragas but not all compositions. Speaks English; may or may not read Telugu/Sanskrit/Tamil.  
**Goal:** Know what's being sung, understand the meaning, follow along without interrupting a neighbor to ask.  
**Key need:** Fast, passive identification — open the app, point the mic, get an answer within seconds.

### Persona 3 — The Student (secondary, future user)
**Profile:** Carnatic music student, learning compositions from a teacher. Wants to use the app to verify which composition is being practiced and access the lyrics + meaning for study.  
**Goal:** Lyrics and meaning instantly, without hunting across multiple websites.  
**Key need:** Accurate composition match + clean lyric display across multiple languages (Telugu, Sanskrit, Tamil, Kannada).

### Persona 4 — The Technical Evaluator (secondary)
**Profile:** College admissions reader, science fair judge, or MIR researcher.  
**Goal:** Understand why this is harder than Shazam and why the technique is different from Western cover-song identification.  
**Key need:** Clear explanation of pitch-contour-based matching vs. chroma-based approaches, and honest accuracy reporting with a real benchmark.

---

## 5. User Stories & Requirements

### Epic 1: Composition Identification

**US-1.1**
```
As a concert-goer,
I want to identify which composition is being performed from a live audio clip,
So that I can know the song name and composer without asking anyone.

Acceptance Criteria:
- System accepts ≥ 30 seconds of live or recorded audio as input
- Returns top-3 ranked composition matches with confidence scores
- Correct match appears in top-1 position for ≥ 70% of held-out test cases
- Works across different artists, shrutis, and tempos of the same composition
- Response time ≤ 5 seconds for a 30-second audio clip on CPU
```

**US-1.2**
```
As the system,
I want to extract tonic-normalized predominant-pitch contours from audio,
So that I can compare melodic identity independently of absolute key/shruti.

Acceptance Criteria:
- Tonic (shruti) estimated from audio using established Carnatic tonic detection
- Pitch contour extracted from predominant melodic line (not chords)
- Contour normalized relative to estimated tonic before matching
- Feature extraction pipeline reproducible and documented
```

**US-1.3**
```
As the system,
I want to match a query pitch contour against a reference catalog using DTW or cross-correlation,
So that I can find the closest known composition despite tempo and performance variation.

Acceptance Criteria:
- Reference catalog contains pitch contours pre-computed for all ~100–150 catalog compositions
- DTW or cross-correlation alignment used (not Euclidean distance, which is tempo-sensitive)
- Matching returns ranked list of compositions with similarity scores
- Matching is robust to partial queries (doesn't require full composition audio)
```

### Epic 2: Raga Classification

**US-2.1**
```
As a concert-goer,
I want to know which raga is being performed,
So that I can understand the melodic framework and mood of the music.

Acceptance Criteria:
- Raga classifier covers ≥ 60 distinct ragas from Saraga + Saraga Audiovisual labeled data
- Classification accuracy ≥ 75% on held-out test set
- Works on improvised (alapana) passages as well as composed sections
- Returns top-3 raga candidates with confidence scores
- Inference time ≤ 3 seconds on a 30-second audio clip
```

**US-2.2**
```
As the system,
I want to extract raga-relevant features from audio (tonic-normalized pitch class distribution),
So that I can classify ragas by their characteristic note usage and phrase patterns.

Acceptance Criteria:
- Features are tonic-normalized (invariant to absolute shruti)
- Feature extraction uses Essentia or librosa pitch estimation
- CNN or TDNN classifier trained on Saraga raga labels
- Classifier is trained on multi-stem audio where available (vocal line preferred)
```

### Epic 3: Tala Detection

**US-3.1**
```
As a concert-goer,
I want to know which tala (rhythmic cycle) is being performed,
So that I can follow the rhythmic structure of the concert.

Acceptance Criteria:
- System identifies tala from audio (e.g. Adi tala, Rupaka, Misra Chapu)
- Beat tracking identifies cycle length; tala classified from cycle structure
- Validated against Saraga's sama (rhythmic cycle boundary) annotations
- Returns tala name with confidence; returns "Unknown" rather than wrong answer if confidence is low
```

### Epic 4: Lyrics & Meaning

**US-4.1**
```
As a concert-goer,
I want to see the full original-language lyrics (sahityam) for an identified composition,
So that I can read along and study the text.

Acceptance Criteria:
- Lyrics database covers hundreds of standard compositions across major composers
- Lyrics include Pallavi, Anupallavi, Charanam sections clearly labeled
- Language displayed: Telugu, Sanskrit, Tamil, or Kannada as appropriate per composition
- Lyrics source is clearly attributed
```

**US-4.2**
```
As a concert-goer,
I want to read an English meaning or explanation of the composition's lyrics,
So that I can understand what is being sung without prior language knowledge.

Acceptance Criteria:
- English meaning generated via Claude or Gemini API, not scraped verbatim from third-party sites
- Meaning covers the devotional/philosophical content of the composition
- Meaning is coherent, accurate to the original text, and readable at a general audience level
- Meaning is generated and cached on first lookup; not re-generated on every query
```

**US-4.3**
```
As the system,
I want to build and maintain a structured lyrics catalog that is independent of the audio ML pipeline,
So that lyrics + meaning can be displayed even when composition matching is uncertain.

Acceptance Criteria:
- Lyrics catalog is a structured JSON/SQLite database keyed by composition ID
- Catalog can be extended without retraining any ML models
- Fallback: if composition match is uncertain (low confidence), lyrics are shown for top-3 candidates
```

### Epic 5: MVP Interface

**US-5.1**
```
As the builder,
I want a Streamlit interface that takes audio input and displays raga, tala, composition match, and lyrics,
So that I can demo the full pipeline end-to-end without building a native app first.

Acceptance Criteria:
- User can upload an audio file or record from mic in the interface
- All four outputs displayed: composition match (top-3), raga, tala, lyrics + meaning
- Confidence scores shown for each prediction
- Interface runs locally on Mac or PC, no cloud dependency for inference
- Demo-ready: starts in ≤ 5 seconds, returns results in ≤ 10 seconds for a 30-second clip
```

---

## 6. Success Metrics

| Metric | Target | Measurement |
|---|---|---|
| Composition match accuracy (top-1) | ≥ 70% | Held-out test set, different renditions from training |
| Raga classification accuracy | ≥ 75% | Held-out test set from Saraga labels |
| Tala identification accuracy | ≥ 80% | Validated against Saraga sama annotations |
| Lyrics catalog coverage | ≥ 200 compositions at launch | Manual catalog count |
| English meaning quality | Coherent + accurate (qualitative review) | Owner review of 20 sample meanings |
| End-to-end inference time | ≤ 10 seconds for 30s audio on CPU | Benchmark on Mac M-series |
| Live demo success rate | System returns results without error for ≥ 9/10 trials | Demo session log |

---

## 7. Scope

### In scope (MVP)
- Composition identification via tonic-normalized pitch-contour matching (DTW/cross-correlation)
- Reference catalog of ~100–150 compositions from Saraga + Saraga Audiovisual
- Raga classification via CNN/TDNN on Saraga-labeled data (~60+ ragas)
- Tala detection via beat tracking + cycle classification
- Lyrics catalog (hundreds of compositions, original-language text)
- English meaning via LLM API (Claude or Gemini), cached per composition
- Streamlit MVP interface (local, no cloud)
- All training and inference on local Mac/PC (Colab Pro for training if needed)

### Out of scope (MVP)
- Native iOS app (phase 2)
- Real-time word-level synchronized lyrics
- Hindustani music support
- Compositions beyond the Saraga-covered catalog for the matching feature
- Raga identification for the full theoretical universe of ragas
- Public deployment or App Store submission
- User accounts, history, or social features
- Instrument identification (vocal only for MVP)

### Phase 2 (post-MVP)
- Native iOS app wrapping the ML core
- App Store submission (requires resolving Saraga CC-NonCommercial license question for commercial use)
- Expanded catalog via self-recorded reference performances
- Word-level lyric sync
- Hindustani music support

---

## 8. Technical Considerations

### Dataset
| Dataset | Size | Coverage | License |
|---|---|---|---|
| Saraga Carnatic | 36.3 hrs, 168 recordings, 19 concerts | ~60+ ragas, annotated (melody, rhythm, structure) | CC-BY-NC-SA 4.0 |
| Saraga Audiovisual (ISMIR 2024) | 60+ hrs, 42 concerts | More ragas, video + pose data | CC-BY-NC-SA 4.0 |

**License flag:** CC-BY-NC-SA means training on this data is fine; redistributing the audio in a commercial product is not. This must be resolved before any App Store release. Inference at runtime uses user-provided audio, not Saraga audio — clarify whether this is a concern with a real lawyer before commercial launch.

### Feature engineering — why not standard chroma
Standard Western cover-song identification uses chroma (harmonic pitch class profile) features and cross-correlates chord progressions. This is a documented poor fit for Carnatic music because:
- Carnatic music is monophonic (no chords); harmonic analysis extracts nothing useful
- Raga identity is carried by characteristic melodic motifs and ornamental patterns (gamakas), not scale membership alone
- Two ragas may share the same theoretical scale but differ in gamaka and characteristic phrases

**Use instead:** tonic-normalized predominant-pitch contours — the same feature type used by CompMusic's own published research on Carnatic raga and motif identification.

### Software stack
| Component | Library | Notes |
|---|---|---|
| Audio processing | Essentia (UPF), librosa | Essentia built by same group as Saraga; has built-in cover-song similarity tools |
| Pitch extraction | Essentia PredominantPitchMelodia | State-of-art for monophonic melody extraction |
| Tonic detection | Essentia TonicIndianArtMusic | Designed specifically for Carnatic/Hindustani |
| Raga classifier | PyTorch or TensorFlow (CNN/TDNN) | Colab Pro for training if needed |
| Composition matching | DTW (dtaidistance library) or cross-correlation | Tempo-invariant alignment |
| Lyrics + meaning | karnatik.com (source); Claude/Gemini API (meaning) | Meaning cached per composition |
| MVP interface | Streamlit | Already used in CRC project — same tooling |
| Data loading | mirdata (saraga_carnatic loader) | Official Python loader for Saraga |

### Architecture (modular)
```
Audio Input
    ↓
Pitch Extraction + Tonic Detection  (Essentia)
    ↓
Feature Layer
    ├── Pitch Contour (for composition matching + tala)
    └── Normalized Pitch-Class Distribution (for raga classification)
         ↓
ML Layer (independent modules, can run in parallel)
    ├── Composition Matcher  (DTW against reference catalog)
    ├── Raga Classifier      (CNN/TDNN)
    └── Tala Detector        (beat tracker + cycle classifier)
         ↓
Lyrics + Meaning Layer
    └── Lookup by composition ID → lyrics DB → LLM meaning (cached)
         ↓
Streamlit Interface (all outputs displayed)
```

### iOS portability note
The ML modules should be exported as CoreML models (.mlmodel) in phase 2, or wrapped via a local API (FastAPI) that the iOS app calls. The Streamlit MVP already enforces separation between ML core and display layer, which is the right architecture for this.

---

## 9. Design & UX Requirements (MVP)

MVP interface is Streamlit — minimal, functional, demo-ready:

- **Input:** File upload (MP3/WAV/FLAC) OR mic recording (30–60 seconds)
- **Output panel 1:** Raga (top-3 with confidence bars)
- **Output panel 2:** Tala (identified cycle + confidence)
- **Output panel 3:** Composition match (top-3 ranked, with composer name)
- **Output panel 4:** Lyrics (sahityam, original language, section-labeled) + English meaning (expandable)
- **Language:** English UI; original-language lyrics displayed as-is
- **Loading state:** Progress indicator during inference (not a blank screen)
- **Error state:** Clear message if audio is too short, too noisy, or no match found

Phase 2 iOS design (out of scope for MVP, but inform architecture):
- Live microphone tap-to-identify UX
- Offline inference (CoreML) for no-WiFi concert venues
- Clean, minimal UI consistent with the tradition's aesthetic

---

## 10. Timeline & Milestones

| Week | Milestone | Hours est. |
|---|---|---|
| 1 | Download Saraga + Saraga Audiovisual; explore annotation format; set up Essentia/librosa/mirdata; begin lyrics catalog from public sources | 12–15 |
| 2 | Build raga classifier (feature extraction → CNN/TDNN → cross-validated accuracy on Saraga labels) | 12–15 |
| 3 | Build tala detection module; validate against Saraga sama annotations | 10–12 |
| 4–5 | Build composition matching pipeline (pitch-contour extraction → reference catalog → DTW matching); evaluate on held-out different-rendition test set | 20–25 total |
| 6 | Build lyrics + LLM meaning pipeline; wire all modules into Streamlit MVP interface | 12–15 |
| 7 | Out-of-dataset generalization testing (own recordings, different artists); threshold tuning; identify failure modes | 10–12 |
| 8 | Polish, documentation, demo recording; structure codebase for iOS portability | 8–10 |

**Total estimated hours: ~85–105 across 8 weeks**

---

## 11. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Composition catalog limited to ~100–150 pieces (not hundreds) | Certain | Medium | Lyrics layer stays broad regardless; expand catalog via self-recorded repertoire post-MVP |
| Western chroma features transfer poorly to Carnatic | Certain (known issue) | Critical | Use tonic-normalized pitch contour; never use chroma for composition matching |
| Saraga CC-NC license restricts App Store release | Medium | High | Use for training only; get legal clarity before any commercial release |
| Scraping third-party lyric translations raises copyright questions | Medium | Medium | Generate fresh meanings via LLM from original (public-domain) lyric text instead |
| No published Carnatic-specific benchmark for composition matching | Certain | Low | Create own benchmark from Saraga; use MIREX Western numbers (~73.5%) as rough reference |
| Raga accuracy limited by small labeled dataset (60+ ragas) | Medium | Medium | Use data augmentation (pitch shift, tempo stretch); report honest accuracy with confidence intervals |
| Tonic detection failure on recordings with heavy audience noise | Low | Medium | Test tonic detection on noisy audio early; implement fallback (manual tonic input) |

---

## 12. Dependencies & Assumptions

### Hard dependencies
- Saraga dataset accessible and downloadable via Zenodo (DOI: 10.5281/zenodo.4301737)
- Saraga Audiovisual dataset accessible via its ISMIR 2024 companion repository
- Essentia installable on Mac (Apple Silicon build available via conda)
- karnatik.com accessible for lyrics sourcing
- Claude or Gemini API access available for meaning generation

### Assumptions
- The Carnatic performance tradition's characteristic approach to raga and composition identity is better captured by melodic-phrase/pitch-contour features than by harmonic features — confirmed in CompMusic literature
- The builder's own performance repertoire can supplement the reference catalog as self-recordings in phase 2
- A 100–150 composition reference catalog is large enough for a compelling demo
- iOS app development is a known-tractable later phase and does not need to be planned in detail for this PRD

---

## 13. Open Questions

| Question | Owner | Priority |
|---|---|---|
| Does the Saraga CC-NC license extend to model weights trained on Saraga audio, or only to the audio itself? | Builder (legal research before App Store launch) | High (for phase 2) |
| Should meanings be pre-generated and cached for all catalog compositions, or generated on first query? | Builder (performance vs. cost tradeoff) | Medium |
| Is there a Saraga-based tonic detection benchmark to validate against, or must we establish our own? | Builder (research in week 1) | Medium |
| Should the Streamlit MVP support mic input on the first pass, or file-upload only? | Builder (latency/complexity tradeoff) | Medium |
| Which compositions in the builder's own performance repertoire should be prioritized for self-recording to expand the catalog? | Builder | Low (phase 2) |
