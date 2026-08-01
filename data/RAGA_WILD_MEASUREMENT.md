# Raga on real wild audio it can answer — the 29 in-tier clips

Executed 2026-07-31/08-01 against `WORKHORSE_RAGA_WILD_BRIEF.md` by the Opus 5
workhorse. Read-only: no retraining, nothing under `models/` written,
`identify_clip.py` untouched, `augment_wild.py` unmodified,
`data/raga_wild/FROZEN_CLIPS.json` unmodified. Every reading, arm, window,
correctness rule, failure category, CI method and pre-score expectation was
registered in `data/raga_wild/PREREGISTRATION.md` and **committed (`463da3d`)
before the harness (`b97a580`, `4c951b3`) and before a single clip was
predicted** — the ordering is in git history, not in file mtimes.

The clip set itself was frozen and committed by the verifier seat at `f67ef98`
before any prediction existed. Selection was closed before this job began and
this job did not reopen it.

**This is a raga measurement on the files in `~/sung_tests`. It is not a
composition measurement and must never be merged into, compared against or
reported alongside the `~/sung_tests --cache-v2` composition scoreboard, which
this job did not touch and which remains the only composition scoreboard.**

**Headline: 16/29 = 55.2% top-1, 95% CI [37.5, 71.6], fused model, `mix` arm,
whole clip. That is the top row of the interpretation table the brief fixed in
advance.** The gates that make the number mean anything are below it, first.

---

## 1. Gate 1 — the hash. PASS, 29/29

Every clip in the frozen, committed list was re-hashed on disk against the
frozen record, sha256 **and** byte length.

```
FROZEN_CLIPS.json: n=29, 29 rows, 18 tier ragas
-> 29/29 verified, 0 mismatch
```

No blocker. The set scored below is bit-for-bit the set the verifier seat froze.

## 2. Gate 3 — source-disjointness against the training corpus. No overlap found

Two independent checks, both run before any classifier was loaded.

### 3a — audio hash, over the whole training corpus

sha256 of **every** audio file the raga model's features were built from:
`data/concert_audio/**` (1238 mp3s, 13 GB — the archive half) and
`saraga1.5_carnatic/**` (991 files, 15 GB — the Saraga half).

| check | result |
|---|---|
| training audio files hashed | **2229** |
| byte-length collisions with any of the 29 | **0** |
| sha256 collisions with any of the 29 | **0** |

The byte-length join is reported because it is *complete* for the failure mode
that bit the Qmax audit — byte-identity implies equal length, so zero length
collisions already excludes byte-identical copies before a single hash is
compared. The full sha256 was computed anyway so the statement needs no
qualifier. **No wild clip is a byte-identical copy of any training file.**

### 3b — identity, against `data/qmax_audit/provenance.json`

Ten of the 29 clips have a **work match** in training: the same composition, in
the same raga, in the archive corpus. Registered in advance as expected and not
contamination — these are famous kritis and the training corpus is Carnatic
concert audio. What matters is whether it is the same *recording*. For every
one of the ten it is not:

| clip | training item | training artist | training dur | clip's source | source dur |
|---|---|---|---|---|---|
| `Jagadanandakaraka__Nata.m4a` | `43-3ss` | — | 448 s | YT `lRHhI8g8RVA` Semmangudi Srinivasa Iyer | 565 s |
| `brOchevarevarura__Khamas.m4a` | `78RPM-M-S-Subbalakshmi` | 78 RPM Pt 2 | 424 s | YT `lFqbACkgpjo` | 2270 s |
| `chakkani rAja__Kharaharapriya.m4a` | `39-ab`, `assorted-artists-78rpm` | Alathur Brothers / 78 RPM Pt 3 | 2033 s, 387 s | YT `ZvzmrIECBl8` | — |
| `nagumomu ganaleni__Saveri.m4a` | `mbk-msg-tvg-concert` | M Balamuralikrishna | 3831 s | YT `j-1FPDdY8sU` Musiri Subramania Iyer | — |
| `nannu pAlimpa__Mōhanaṁ.mp3` | `Bidaram-Krishnappa`, `tsk-whistle` | 78 RPM Pt 3 / — | 212 s, 1048 s | not recorded | — |
| `nidhi chAla sukhamA__Kalyani.m4a` | `kvn-229` | K V Narayanaswamy | 854 s | YT `staBlOuHEt0` Nedunuri Krishnamurthy | 1041 s |
| `rAma nannu brOvara__Harikambhoji.m4a` | `78RPMDKPattammal` | 78 RPM Pt 2 | 380 s | YT `QoNfl2abIsI` Mandolin U. Shrinivas | 310 s |
| `rAma nee__Karaharapriya.m4a` | `78RPM-S-V-Subbiah-Bhagavathar` | 78 RPM Pt 2 | 323 s | YT `Tqv19g98LXI` M L Vasanthakumari | 2614 s |
| `raghuvara__Kamavardani.m4a` | `19-ab` | Alathur Brothers | 611 s | YT `16dIDxk9tbE` K.V. Narayanaswamy | 720 s |
| `siddhi vinAyakam__Shanmukhapriya.m4a` | `1-MR-VT-ManakkalSriram` | Manakkal Rangarajan | 626 s | YT `_SJCsV-1O2s` Maharajapuram Santhanam | 350 s |

Different artist and different source duration in every case where both are
recoverable. **Zero recording matches. Nothing was scored with and without a
contaminated clip because no clip qualified.**

The remaining 19 clips have **no work match at all**, so no contamination
candidate exists for them. 17 of the 29 carry a specific YouTube source URL and
window in `~/sung_tests/fetch_manifest.tsv`; 12 (the `.mp3`s) have no recorded
source, and for those the hash check is the whole of the evidence.

**Residual risk, stated rather than hidden.** A byte hash cannot see a
re-encode. Several archive training items are public-domain 78 RPM transfers and
YouTube carries re-uploads of exactly that material, so a re-encoded overlap is
the one mode neither check would catch. It is bounded to the ten work-matched
clips, and for those the artist and duration evidence above points away from it
in every case.

## 3. Gate 2 and the labels — what the number is provisional on

**All 29 clips decoded and all 29 produced a usable contour in every arm.** The
registered failure taxonomy, mutually exclusive, never summed:

| arm | window | scored | no_contour | min_voiced | tdms_none | demucs_fail | audio_unavailable |
|---|---|---|---|---|---|---|---|
| `mix` | whole | **29** | 0 | 0 | 0 | — | 0 |
| `mix` | 60 s | **8** | 0 | 0 | 0 | — | 0 |
| `mix_voiceband` | whole / 60 s | **29 / 8** | 0 | 0 | 0 | — | 0 |
| `demucs` | whole / 60 s | **29 / 8** | 0 | 0 | 0 | **0** | 0 |

**The tonic fallback never fired.** `TonicIndianArtMusic` returned a value
inside `identify_clip.py`'s own [80, 400] Hz band on all 29 clips, so
`identify_clip.py`'s 146.83 Hz default was used zero times. Voicing density is
0.699 mean [0.564, 0.824] and voiced melody averages 43.9 s per clip
[30.7, 57.1] — density sits squarely inside the archive corpus's own 0.671-0.693
band, so the wild clips are not a different regime for this feature.

**The labels have never been audited and every number in this document is
provisional on them.** They come from the filename convention
`<title>__<raga>.<ext>`. Printed in full so a musician can read them:

| # | file | raga_label (filename) | raga_canonical | dur | OOC | source |
|---|---|---|---|---|---|---|
| 1 | `Amba Kamakshi__Bhairavi.mp3` | Bhairavi | Bhairavi | 70.7 s |  | not recorded |
| 2 | `Enu Dhanyalo Lakumi__Todi.mp3` | Todi | Tōḍi | 65.7 s |  | not recorded |
| 3 | `Jagadanandakaraka__Nata.m4a` | Nata | Nāṭa | 60.0 s |  | YouTube `lRHhI8g8RVA` |
| 4 | `Kaddanuvariki__Todi.mp3` | Todi | Tōḍi | 84.8 s |  | not recorded |
| 5 | `Koluvamaregada kodandapani__Tōḍi.mp3` | Tōḍi | Tōḍi | 67.2 s |  | not recorded |
| 6 | `Maithreem Bhajata__Kalyani__OOC.mp3` | Kalyani | Kalyāṇi | 84.3 s | yes | not recorded |
| 7 | `Ninnukori Yunnanura__Mohanam.m4a` | Mohanam | Mōhanaṁ | 60.0 s |  | YouTube `pHO_AO6X_JM` |
| 8 | `Pillangoviya__Mohanam.mp3` | Mohanam | Mōhanaṁ | 56.0 s |  | not recorded |
| 9 | `Ranga Baro__Sindhu Bhairavi.mp3` | Sindhu Bhairavi | Sindhubhairavi | 62.6 s |  | not recorded |
| 10 | `Thaye Yashoda__Todi__OOC.mp3` | Todi | Tōḍi | 57.9 s | yes | not recorded |
| 11 | `bhajarE bhaja mAnasa__Kanada.m4a` | Kanada | Kānaḍa | 60.0 s |  | YouTube `zbY3OFKjYWQ` |
| 12 | `bhajare__Kalyani.m4a` | Kalyani | Kalyāṇi | 60.0 s |  | YouTube `ad6UhYwTXXQ` |
| 13 | `brOchevarevarura__Khamas.m4a` | Khamas | Kamās | 60.0 s |  | YouTube `lFqbACkgpjo` |
| 14 | `chakkani rAja__Kharaharapriya.m4a` | Kharaharapriya | Karaharapriya | 60.0 s |  | YouTube `ZvzmrIECBl8` |
| 15 | `entara__Harikambhoji.m4a` | Harikambhoji | Harikāmbhōji | 60.0 s |  | YouTube `WUkViRiTB_o` |
| 16 | `himAdrisutE__Kalyani.m4a` | Kalyani | Kalyāṇi | 60.0 s |  | YouTube `rO9gXgJ721U` |
| 17 | `nagumomu ganaleni__Saveri.m4a` | Saveri | Sāvēri | 60.0 s |  | YouTube `j-1FPDdY8sU` |
| 18 | `nannu pAlimpa__Mōhanaṁ.mp3` | Mōhanaṁ | Mōhanaṁ | 83.9 s |  | not recorded |
| 19 | `nidhi chAla sukhamA__Kalyani.m4a` | Kalyani | Kalyāṇi | 60.0 s |  | YouTube `staBlOuHEt0` |
| 20 | `rAma nannu brOvara__Harikambhoji.m4a` | Harikambhoji | Harikāmbhōji | 60.0 s |  | YouTube `QoNfl2abIsI` |
| 21 | `rAma nee__Karaharapriya.m4a` | Karaharapriya | Karaharapriya | 60.0 s |  | YouTube `Tqv19g98LXI` |
| 22 | `raghuvara__Kamavardani.m4a` | Kamavardani | Kāmavardani | 60.0 s |  | YouTube `16dIDxk9tbE` |
| 23 | `sarOja daLa nEtri__Śankarābharaṇaṁ.mp3` | Śankarābharaṇaṁ | Śankarābharaṇaṁ | 78.9 s |  | not recorded |
| 24 | `sarasijanAba murArE__Tōḍi.mp3` | Tōḍi | Tōḍi | 43.2 s |  | not recorded |
| 25 | `siddhi vinAyakam__Shanmukhapriya.m4a` | Shanmukhapriya | Ṣanmukhapriya | 60.0 s |  | YouTube `_SJCsV-1O2s` |
| 26 | `swAminatha__Nata.m4a` | Nata | Nāṭa | 60.0 s |  | YouTube `CEt-viITlws` |
| 27 | `vAtApi gaNapathim__Hamsadhvāni.mp3` | Hamsadhvāni | Hamsadhvāni | 52.8 s |  | not recorded |
| 28 | `yArO ivar yArO__Bhairavi.m4a` | Bhairavi | Bhairavi | 60.0 s |  | YouTube `RWIZJQ9QT6U` |
| 29 | `yEnATi mOmu palamu__Bhairavi.m4a` | Bhairavi | Bhairavi | 60.0 s |  | YouTube `8Ub9i6OXirQ` |

**Two clips I would ask a musician about**, offered as questions from a
non-musician and not as corrections, and flagged under the brief's "if you
believe a clip should not be in the set, say so and report the number both
ways":

- **#17 `nagumomu ganaleni__Saveri`.** The Tyāgarāja kriti of that name is
  normally sung in **Ābhēri**, which is *not* in the 18-raga tier — if that is
  what this recording is, the clip should never have been eligible. Noted
  against itself: the archive training corpus independently carries the same
  title under a `Sāvēri` directory, so either the label is right or both
  inherited the same error.
- **#6 `Maithreem Bhajata__Kalyani`.** Usually rendered in **Yamunākalyāṇi**, or
  as a rāgamālika, neither of which is in the tier.

**Both are misses under the current labels, so removing them raises the
headline rather than lowering it: 16/27 = 59.3% [40.7, 75.5] top-1 instead of
16/29 = 55.2% [37.5, 71.6].** This is a post-hoc sensitivity, was not
registered, and is reported only because the brief requires the number both
ways. **The headline stays 16/29 = 55.2%.** Nothing else in this document uses
the 27-clip figure.

## 4. Windows

Eight clips exceed 60 s and were scored **both** ways — the whole clip and a
60 s window at the duration curve's own seeded offset
(`np.random.default_rng(42)`, three fractions per clip in sorted-filename order,
index 0, `start = u0 · (dur − 60)`). The other 21 were scored on what exists;
their lengths (43.2-60.0 s) are in the label table.

| clip | duration | `u0` | 60 s window starts at |
|---|---|---|---|
| `Amba Kamakshi__Bhairavi.mp3` | 70.7 s | 0.7740 | 8.28 s |
| `Enu Dhanyalo Lakumi__Todi.mp3` | 65.7 s | 0.6974 | 3.97 s |
| `Kaddanuvariki__Todi.mp3` | 84.8 s | 0.4504 | 11.18 s |
| `Koluvamaregada kodandapani__Tōḍi.mp3` | 67.2 s | 0.6439 | 4.67 s |
| `Maithreem Bhajata__Kalyani__OOC.mp3` | 84.3 s | 0.2272 | 5.52 s |
| `Ranga Baro__Sindhu Bhairavi.mp3` | 62.6 s | 0.7784 | 2.05 s |
| `nannu pAlimpa__Mōhanaṁ.mp3` | 83.9 s | 0.0074 | 0.18 s |
| `sarOja daLa nEtri__Śankarābharaṇaṁ.mp3` | 78.9 s | 0.5592 | 10.55 s |

Seventeen of the 29 are exactly 60.0 s because they were auto-fetched as 60 s
windows of longer sources; that is a property of the frozen set, not a choice
made here. One clip (`yArO ivar yArO__Bhairavi.m4a`) is an m4a whose first
stream is cover-art video; it decoded normally and its audio is 60.0 s.

**"Best available window" was defined in the prereg as the whole clip** — the
longest audio each clip actually has — before any duration was looked at in a
scoring context, and the duration curve is monotone in duration, so this is by
construction and not by outcome.

---

## 5. The per-clip table

Fused model, `mix` arm. Every one of the 29 can be inspected by hand; at n = 29
this table carries more than the mean does.

| clip | dur | truth | top-1 (32-class) | p | rank | hit | top-1 (18-class) | hit | 60 s top-1 | hit |
|---|---|---|---|---|---|---|---|---|---|---|
| `Amba Kamakshi__Bhairavi.mp3` | 70.7 s | Bhairavi | Bhairavi | 0.15 | 1 | **Y** | Bhairavi | **Y** | Bhairavi | **Y** |
| `Enu Dhanyalo Lakumi__Todi.mp3` | 65.7 s | Tōḍi | Vasanta | 0.07 | 2 | t3 | Vasanta | t3 | Nāṭa | t3 |
| `Jagadanandakaraka__Nata.m4a` | 60.0 s | Nāṭa | Nāṭa | 0.22 | 1 | **Y** | Nāṭa | **Y** | — | — |
| `Kaddanuvariki__Todi.mp3` | 84.8 s | Tōḍi | Tōḍi | 0.25 | 1 | **Y** | Tōḍi | **Y** | Tōḍi | **Y** |
| `Koluvamaregada kodandapani__Tōḍi.mp3` | 67.2 s | Tōḍi | Tōḍi | 0.20 | 1 | **Y** | Tōḍi | **Y** | Sāvēri | t3 |
| `Maithreem Bhajata__Kalyani__OOC.mp3` | 84.3 s | Kalyāṇi | Mōhanaṁ | 0.10 | 4 | n | Mōhanaṁ | t3 | Mōhanaṁ | t3 |
| `Ninnukori Yunnanura__Mohanam.m4a` | 60.0 s | Mōhanaṁ | Hindōḷaṁ | 0.35 | 28 | n | Sindhubhairavi | n | — | — |
| `Pillangoviya__Mohanam.mp3` | 56.0 s | Mōhanaṁ | Mōhanaṁ | 0.22 | 1 | **Y** | Mōhanaṁ | **Y** | — | — |
| `Ranga Baro__Sindhu Bhairavi.mp3` | 62.6 s | Sindhubhairavi | Madhyamāvati | 0.12 | 22 | n | Karaharapriya | n | Madhyamāvati | n |
| `Thaye Yashoda__Todi__OOC.mp3` | 57.9 s | Tōḍi | Tōḍi | 0.21 | 1 | **Y** | Tōḍi | **Y** | — | — |
| `bhajarE bhaja mAnasa__Kanada.m4a` | 60.0 s | Kānaḍa | Aṭāna | 0.11 | 30 | n | Aṭāna | n | — | — |
| `bhajare__Kalyani.m4a` | 60.0 s | Kalyāṇi | Śankarābharaṇaṁ | 0.11 | 21 | n | Śankarābharaṇaṁ | n | — | — |
| `brOchevarevarura__Khamas.m4a` | 60.0 s | Kamās | Kamās | 0.53 | 1 | **Y** | Kamās | **Y** | — | — |
| `chakkani rAja__Kharaharapriya.m4a` | 60.0 s | Karaharapriya | Karaharapriya | 0.13 | 1 | **Y** | Karaharapriya | **Y** | — | — |
| `entara__Harikambhoji.m4a` | 60.0 s | Harikāmbhōji | Kamās | 0.34 | 2 | t3 | Kamās | t3 | — | — |
| `himAdrisutE__Kalyani.m4a` | 60.0 s | Kalyāṇi | Śankarābharaṇaṁ | 0.16 | 5 | n | Śankarābharaṇaṁ | n | — | — |
| `nagumomu ganaleni__Saveri.m4a` | 60.0 s | Sāvēri | Karaharapriya | 0.13 | 7 | n | Karaharapriya | t3 | — | — |
| `nannu pAlimpa__Mōhanaṁ.mp3` | 83.9 s | Mōhanaṁ | Mōhanaṁ | 0.49 | 1 | **Y** | Mōhanaṁ | **Y** | Mōhanaṁ | **Y** |
| `nidhi chAla sukhamA__Kalyani.m4a` | 60.0 s | Kalyāṇi | Kalyāṇi | 0.37 | 1 | **Y** | Kalyāṇi | **Y** | — | — |
| `rAma nannu brOvara__Harikambhoji.m4a` | 60.0 s | Harikāmbhōji | Kamās | 0.22 | 2 | t3 | Kamās | t3 | — | — |
| `rAma nee__Karaharapriya.m4a` | 60.0 s | Karaharapriya | Aṭāna | 0.17 | 5 | n | Aṭāna | n | — | — |
| `raghuvara__Kamavardani.m4a` | 60.0 s | Kāmavardani | Kāmavardani | 0.42 | 1 | **Y** | Kāmavardani | **Y** | — | — |
| `sarOja daLa nEtri__Śankarābharaṇaṁ.mp3` | 78.9 s | Śankarābharaṇaṁ | Bēgaḍa | 0.25 | 4 | n | Harikāmbhōji | t3 | Bēgaḍa | n |
| `sarasijanAba murArE__Tōḍi.mp3` | 43.2 s | Tōḍi | Tōḍi | 0.20 | 1 | **Y** | Tōḍi | **Y** | — | — |
| `siddhi vinAyakam__Shanmukhapriya.m4a` | 60.0 s | Ṣanmukhapriya | Ṣanmukhapriya | 0.10 | 1 | **Y** | Ṣanmukhapriya | **Y** | — | — |
| `swAminatha__Nata.m4a` | 60.0 s | Nāṭa | Nāṭa | 0.53 | 1 | **Y** | Nāṭa | **Y** | — | — |
| `vAtApi gaNapathim__Hamsadhvāni.mp3` | 52.8 s | Hamsadhvāni | Bhairavi | 0.12 | 25 | n | Bhairavi | n | — | — |
| `yArO ivar yArO__Bhairavi.m4a` | 60.0 s | Bhairavi | Bhairavi | 0.21 | 1 | **Y** | Bhairavi | **Y** | — | — |
| `yEnATi mOmu palamu__Bhairavi.m4a` | 60.0 s | Bhairavi | Bhairavi | 0.35 | 1 | **Y** | Bhairavi | **Y** | — | — |

---

## 6. Top-1 and top-3, with a CI beside every percentage

n = 29 clips, unit = the clip, interval = Wilson score. **No point estimate
appears anywhere in this document without its interval.**

**Exported-model wrinkle, registered in the prereg before scoring:** the
exported `models/raga_v3_*` model has **32 classes** (`min_tracks = 20`), not
the 18 of the tier that selected the clips. The 32-class read-out is what a
product would emit and is the primary; the 18-class restricted read-out
(posterior restricted to the tier and renormalised) is the figure directly
comparable to the domain job's 48.7% and to the 1/18 floor. All 18 tier ragas
are present in the model's label set.

### Whole clip, n = 29 — the primary window

| model | scope | arm | top-1 (95% CI) | top-3 (95% CI) |
|---|---|---|---|---|
| **fused** | **32-class** | **`mix`** | **16/29 = 55.2% [37.5, 71.6]** | **19/29 = 65.5% [47.3, 80.1]** |
| fused | 18-class | `mix` | 16/29 = 55.2% [37.5, 71.6] | 22/29 = 75.9% [57.9, 87.8] |
| fused | 32-class | `demucs` | 15/29 = 51.7% [34.4, 68.6] | 18/29 = 62.1% [44.0, 77.3] |
| fused | 18-class | `demucs` | 15/29 = 51.7% [34.4, 68.6] | 22/29 = 75.9% [57.9, 87.8] |
| fused | 32-class | `mix_voiceband` | 14/29 = 48.3% [31.4, 65.6] | 19/29 = 65.5% [47.3, 80.1] |
| TDMS-only | 32-class | `mix` | 12/29 = 41.4% [25.5, 59.3] | 18/29 = 62.1% [44.0, 77.3] |
| TDMS-only | 18-class | `mix` | 12/29 = 41.4% [25.5, 59.3] | 20/29 = 69.0% [50.8, 82.7] |
| TDMS-only | 32-class | `demucs` | 14/29 = 48.3% [31.4, 65.6] | 17/29 = 58.6% [40.7, 74.5] |
| TDMS-only | 18-class | `demucs` | 14/29 = 48.3% [31.4, 65.6] | 18/29 = 62.1% [44.0, 77.3] |

### The seeded 60 s window, n = 8 — only the clips that have one

Paired against the *same eight* clips' whole-clip result, so this is a window
comparison and not a subset comparison:

| arm / scope | whole clip | 60 s window | exact McNemar |
|---|---|---|---|
| fused, 32-class, `mix` | 4/8 = 50.0% [21.5, 78.5] | 3/8 = 37.5% [13.7, 69.4] | p = 1.000 |
| fused, 18-class, `mix` | 4/8 = 50.0% [21.5, 78.5] | 3/8 = 37.5% [13.7, 69.4] | p = 1.000 |

The 60 s window is one clip worse on eight clips. **n = 8 resolves nothing** and
this is reported as inventory, not as a duration result — the duration curve
already measured that question properly.

### `demucs` against `mix` — the arm the brief called decisive for what happens next

Paired, exact McNemar on the discordant pairs, fused model, whole clip, all 29:

```
demucs-only correct:  1   (rAma nannu brOvara__Harikambhoji.m4a)
mix-only correct:     2   (Koluvamaregada kodandapani__Tōḍi.mp3,
                           siddhi vinAyakam__Shanmukhapriya.m4a)
exact p = 1.000
```

**Separation does not materially beat the mix on this set — it is 3.5 points
below it, one fix against two breaks, and the difference is indistinguishable
from zero.** On the TDMS-only secondary the sign flips (48.3% vs 41.4%, +6.9 pp
to `demucs`), which at n = 29 is the same non-result read the other way round.
The brief's condition — "if it materially beats `mix`, separation is
load-bearing in the field and any product must budget for it" — **is not met**.
One asymmetry belongs with that and was registered in advance: the *fused*
model's histogram half is Demucs-derived by construction in **both** arms
(`raga_v2_pipeline.py` defines that feature as pyin on the htdemucs vocal), so
the clean separation contrast is the TDMS-only row, which is the one that
mildly favours `demucs`.

### `mix_voiceband` — the registered non-gating diagnostic

`identify_clip.py`'s wild-clip melodia constraint (`minFrequency=90,
maxFrequency=900, voicingTolerance=0.6`), which `HANDOFF_CLIP_ID.md` §5 records
as the thing that "fixed melody extraction — keep it", scores **48.3%
[31.4, 65.6]** against the training cache's unconstrained parameters at 55.2%:
two breaks, zero fixes, no clip rescued. **On these 29 clips the constraint
costs and never pays.** It gates nothing and this is a diagnostic, not a
recommendation.

### Fusion is doing real work

The fused model beats TDMS-only 16/29 against 12/29 with **four fixes and zero
breaks** (`Amba Kamakshi`, `chakkani rAja`, `siddhi vinAyakam`,
`yArO ivar yArO`). The histogram half is not decoration on this set.

### Rank of the true raga, and where the number sits above chance

| scope | median rank | mean rank | truth in top-5 | worst rank |
|---|---|---|---|---|
| 32-class | **1** | 6.0 | 23/29 | 30 of 32 |
| 18-class | **1** | 3.9 | 24/29 | 17 of 18 |

The median rank of the true raga is 1 and the mean is dragged by a small number
of catastrophic misses — five clips put the truth at rank 21-30 of 32
(`Ninnukori Yunnanura`, `Ranga Baro`, `bhajarE bhaja mAnasa`, `bhajare`,
`vAtApi gaNapathim`). **The failure mode is bimodal: mostly right at rank 1, or
badly wrong at the bottom of the list. There is very little middle.**

Reference floors on this set: uniform 1/18 = 5.6%, uniform 1/32 = 3.1%,
class-prior expectation Σpᵢ² = 9.4%, and the best possible constant guess
(always answer Tōḍi) = 5/29 = **17.2%**. The 55.2% is 3.2× the best constant
guess, and the model emitted **15 distinct classes across the 29 clips** (most
frequent: Bhairavi 4, Tōḍi 4, Mōhanaṁ 3), so it is not winning by matching the
set's skew.

### Per-raga, primary cell

| raga | n | top-1 | top-3 |
|---|---|---|---|
| Bhairavi | 3 | 3/3 | 3/3 |
| Tōḍi | 5 | 4/5 | 5/5 |
| Nāṭa | 2 | 2/2 | 2/2 |
| Mōhanaṁ | 3 | 2/3 | 2/3 |
| Kamās | 1 | 1/1 | 1/1 |
| Kāmavardani | 1 | 1/1 | 1/1 |
| Ṣanmukhapriya | 1 | 1/1 | 1/1 |
| Karaharapriya | 2 | 1/2 | 1/2 |
| Kalyāṇi | 4 | 1/4 | 1/4 |
| Harikāmbhōji | 2 | 0/2 | 2/2 |
| Hamsadhvāni | 1 | 0/1 | 0/1 |
| Kānaḍa | 1 | 0/1 | 0/1 |
| Sindhubhairavi | 1 | 0/1 | 0/1 |
| Sāvēri | 1 | 0/1 | 0/1 |
| Śankarābharaṇaṁ | 1 | 0/1 | 0/1 |

At one to five clips per raga **no per-raga cell means anything on its own** and
none should be quoted. It is here because the brief requires the per-clip level
of detail. The one pattern worth naming, and only as a pattern: Kalyāṇi goes
1/4, and both misses that were checkable went to Śankarābharaṇaṁ — a
neighbouring scale — while both Harikāmbhōji misses went to Kamās, which shares
its scale. The confusions are musically adjacent rather than random.

---

## 7. How the pre-registered expectations came out

Written down before scoring so they could be wrong. Three of five were.

| # | registered expectation | outcome |
|---|---|---|
| 1 | contour failures 0-2 clips | **right** — 0 of 29, in every arm |
| 2 | tonic fallback on 0-5 of 29 | **right at the edge** — 0. The second half of that expectation (that tonic error would be a larger share of the damage here than the domain job's 3:1) is **not testable** without an oracle tonic and was not measured |
| 3 | 32-class read-out 5-12 pp below 18-class | **wrong for top-1** (identical, 0 pp) and right for top-3 (10.4 pp). Restricting the label set never changed which class was ranked first — it only pulled true ragas into the top three from just outside it |
| 4 | primary lands in the 20-40% band | **wrong** — 55.2%, the top row |
| 5 | `demucs` beats `mix` by an unresolvable 0-15 pp | **wrong in sign** — `demucs` is 3.5 pp *below* `mix` on the fused model, and unresolvable |

---

## 8. Verdict against the interpretation table fixed in advance

The table is fixed on **top-1 over the 29, `mix` arm, best available window**:
**16/29 = 55.2%, 95% CI [37.5, 71.6]**, whose interval contains the domain job's
`field_all` simulation of 48.7% and excludes both the 1/18 ≈ 5.6% chance floor
and the 17.2% best-constant-guess floor. **That is the top row — "≥ 40% (CI
overlapping 48.7%): the simulation was valid and raga survives real field audio;
the 0/10 was a coverage artifact and nothing more."** The gates that had to hold
for that to mean anything do hold: all 29 clips verified bit-for-bit against the
frozen list, all 29 produced a contour in every arm, no clip's audio is a
byte-identical copy of any of the 2229 training files, no work match is the same
recording, and the tonic fallback never fired — so the brief's fourth row, "too
few clips survive the checks", does not apply and n is not the finding. The
`demucs` arm, which the brief called decisive for what happens next, **does not
materially beat `mix`** (51.7% against 55.2%, one fix against two breaks,
exact p = 1.000), so on this evidence separation is not load-bearing for raga in
the field the way `HANDOFF_SESSION_0719.md` §4.1 claimed it is for the ASR path.
The three things that must be carried with the number are that **the labels are
unaudited** and two of them are worth a musician's eye, that **n = 29 over 18
classes resolves nothing finer than the row it lands in**, and that this job
**cannot attribute** the distance between the historical 0/10 and 55.2% — the
0/10 was produced by `identify_clip.raga_top5`, a different model
(`raga_clip_rf.pkl`) with a different tonic convention (the 12-rotation vote
that `HANDOFF_CLIP_ID.md` §5 records as anti-informative), on ten clips whose
identities were never recorded, so coverage, model and tonic are all confounded
in that comparison and none of them can be credited here.

**The decision about what to do with this belongs to the verifier seat.** This
document states the measurement and the row.

---

## 9. Scope — what this does not establish

- **It graduates nothing.** No model was trained, nothing under `models/` was
  written, `identify_clip.py` was not touched, `augment_wild.py` was not
  modified, and the frozen clip list was not edited.
- **It is not a composition result.** `~/sung_tests --cache-v2` composition
  numbers are untouched by this job and remain the only composition scoreboard.
  Nothing here may be merged into or reported alongside them.
- **No conclusion about the lyrics-ASR path may be drawn from it**, in either
  direction. Different channel, different features, different model. The
  duration KILL on that channel is a separate result and is not touched.
- **The labels are unaudited.** At n = 29 one mislabelled clip is 3.4 points.
- **It measures 43-85 s clips of the 18-raga tier's ragas only.** It says
  nothing about the 52 clips in `~/sung_tests` whose raga is outside the tier,
  where the classifier still cannot be right, nor about what happens when the
  true raga is outside the model's 32 classes — every clip here was inside them
  by construction.
- **The 32-class model was asked a question its label set could always answer.**
  A product would face clips whose raga is not in the 32, and this job measures
  nothing about that case.
- The `demucs` arm was run on 29 clips; a null at n = 29 is not evidence of
  absence, only absence of evidence.

---

## 10. Artifacts

| file | what |
|---|---|
| `data/raga_wild/FROZEN_CLIPS.json` | the frozen set, committed at `f67ef98` by the verifier seat |
| `data/raga_wild/PREREGISTRATION.md` | registered and committed (`463da3d`) before the harness and before any prediction |
| `scripts/raga_wild_protocol.py` | hash gate, label table, disjointness, window inventory — no score |
| `scripts/raga_wild_features.py` | melodia / tonic / TDMS per arm, Demucs, the production 480-dim histogram |
| `scripts/raga_wild_score.py` | the exported models, both scopes, Wilson CIs, McNemar, per-clip |
| `data/raga_wild/protocol.json` | gate output, machine-readable |
| `data/raga_wild/results.json` | every cell, every per-clip row |
| `data/raga_wild/tables.md` | the two tables above, generated from `results.json` |
| `data/raga_wild/protocol.log`, `features.log`, `score.log` | raw run output |
| `data/raga_wild/rows/*.npz` | per (clip, window) features — 2 MB, committed, so `raga_wild_score.py` re-runs in seconds without the 34-minute Demucs/pyin rebuild |
