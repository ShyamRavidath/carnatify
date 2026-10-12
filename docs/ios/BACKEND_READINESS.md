# Backend readiness for a native iOS client

Audit of `backend/main.py` at `5715742` (branch `probe/duration-and-negative-arm`), 2026-10-11.
Nothing in the backend was changed. Tags: **[M]** measured locally (FastAPI `TestClient`, `venv_train`,
real models, no mocks); **[C]** read from code; **[D]** from DEPLOY.md. Harness, clips and raw JSONL
results: session scratchpad (`harness.py`, `results_*.jsonl`); not committed.

Test audio: one excerpt of `data/long_concerts/audio/long_concert_2.mp3` (600 s in; the Hindolam
alapana stretch), cut to 30 s and 180 s and encoded as iOS would: AAC-LC `.m4a` 44.1 kHz mono,
AAC-LC 48 kHz mono, an `afconvert -f m4af -d aac` file (Apple's own encoder), 16-bit LPCM `.caf`,
16-bit `.wav`, plus a 180 s 48 kHz float32 `.caf` (34.6 MB) and an 8 s clip.

**Latency caveat:** this Mac (M5, 10 cores) was heavily loaded during the run (load average 35-58,
an iOS Simulator and other agents running). Timings are upper bounds for this machine and lower
bounds for a 2-vCPU HF Space; the same 30 s Demucs job took 25 s and 171 s in different minutes.

## 1. Route inventory

Python env: tests and this audit use `venv_train/bin/python` (HANDOFF commands use it; it has
whisper/faster-whisper, `venv` does not). No route needs a secret except `/meaning` on a cache miss.

| Route | Input | 200 response keys | Errors (measured unless noted) | Limit |
|---|---|---|---|---|
| `GET /health` | none | `{status:"ok"}` [M] | none | none |
| `GET /tracks` | none | list of 197 `{track_id,title,raga,tonic}` [M] | none | none |
| `POST /predict` | JSON `{track_id}` (Saraga demo track) | `{raga:[{name,confidence}], matches:[{title,score,track_id}]}` [M] | 404 unknown id; 422 pydantic list | none |
| `POST /predict-audio` | multipart field `file` | `{raga:[{name,confidence}]x3, matches:[{title,score,track_id}]x3, tonic, tonic_method:"essentia", duration}` [M] | 413 >30 MB; 415 content-type; 422 decode / tonic / Demucs failure / too little pitch | 2/min/IP |
| `POST /identify-raga` | multipart field `file` | `{asserted:false, answered, reason, candidates:[{raga,probability,score}]x5, signals:{max_score,margin,softmax_max}, gate:{name,signal,threshold,status,source,would_accept}\|null, tonic, voiced_s, duration, model:{name,sha256,path,feature_version,representation,window_s,n_classes}}` [M] | 503 no registry/bundle [C]; 413; 415; 422 decode / <10 s | 4/min/IP |
| `POST /identify` | multipart `file`, query `fast` (bool) | `{query_id, compositions:[{title,score,ragas}], composition_confidence, clip_type, asr_variant, transcript, message, raga_from_catalog?, raga_confidence, raga:[{name,confidence}]}`; `raga_from_catalog` is absent when `clip_type:"no_lyrics"`; `raga_confidence` is always `"low"` because the route overwrites the matcher's value [C+M] | 413; 415; 422 decode / <15 s | 2/min/IP |
| `POST /feedback` | JSON `{query_id, verdict: confirmed\|rejected\|not_in_catalog, chosen_title?, user_title?, user_raga?}` | `{status:"recorded", thanks:true}` [M] | 422 bad verdict (string `detail`) or missing field (list `detail`) | 10/min/IP |
| `GET /meaning/{title}` | path (title, URL-encoded) | `{title, composer, meaning}` [M] | 404 not in catalog [M]; 502 Gemini failure or missing key [C] | none |

What an iOS v1 needs:
- **Raga from a recorded clip:** `/identify-raga`. It is the only route on the audited single
  contract (`raga_runtime`), it never asserts, and it was the only one stable across codecs (§2).
  `/predict-audio` is the legacy path (Demucs + pyin + old `.pkl`); do not build on it.
- **Composition from a clip:** `/identify` (lyrics-first ASR). Needs whisper large-v3-turbo on the server.
- **Meaning:** `/meaning/{title}` using a title returned by `/identify`. Only 280 of 3,252 catalog
  rows have a cached meaning; any other catalog title triggers a live Gemini call (costs money,
  needs `GEMINI_API_KEY`; not exercised here). Cached text quality varies: `Evari Bodhana` returns
  "Meaning is available here at Shivkumar Kalyanaraman's site." [M].
- **Feedback:** `/feedback` with the `query_id` from `/identify`. There is no feedback path for
  `/identify-raga` (it returns no query id and logs nothing).
- `/tracks` and `/predict` serve the web demo's Saraga track picker; not needed on iOS.

Error shape is inconsistent [M]: `HTTPException` gives `{detail:"string"}`, validation errors give
`{detail:[{type,loc,msg,input}]}`, and slowapi's 429 gives `{error:"Rate limit exceeded: 2 per 1 minute"}`
(no `Retry-After` header). A Swift client needs three decoders or a server-side normalisation.

## 2. iOS audio formats [M]

Decode is `librosa.load` (soundfile first, then audioread/ffmpeg fallback, which librosa marks
deprecated and slated for removal in 1.0). The Dockerfile installs `ffmpeg` and `libsndfile1`, so
the fallback exists on the Space [C].

The gate is `_upload_suffix(content_type)`: a substring match of the multipart part's
`Content-Type` against `ogg, opus, mp4, m4a, aac, webm, mpeg, mp3, wav`. The bytes are never
sniffed for the gate; the suffix only names the temp file, and ffmpeg/libsndfile then detect the
real container. Result on `/identify-raga`, every file x every content type (80 calls):

| Part `Content-Type` | AAC .m4a 44.1k | AAC .m4a 48k | afconvert .m4a | LPCM .caf | .wav |
|---|---|---|---|---|---|
| `audio/m4a`, `audio/x-m4a`, `audio/mp4`, `audio/aac` | 200 | 200 | 200 | 200 | 200 |
| `audio/wav`, `audio/vnd.wave` (UTType.wav's MIME) | 200 | 200 | 200 | 200 | 200 |
| `audio/x-caf` (UTType CAF's MIME) | **415** | **415** | **415** | **415** | **415** |
| `application/octet-stream` (common Swift default) | **415** | **415** | **415** | **415** | **415** |
| empty / missing part type | **415** "content-type: none" | | | | |

- No crashes, no 500s. Mislabelled files decode fine (a CAF sent as `audio/m4a` returns 200),
  which proves the content-type gate rejects files the decoder can read.
- `/predict-audio` and `/identify` use the same `_upload_suffix`; measured identical 415s on
  `/predict-audio` for `audio/x-caf` and `application/octet-stream`.
- A 180 s recording in 48 kHz float32 CAF (a plausible `AVAudioEngine` tap dump) is 34.6 MB and
  gets **413**. AAC at 64 kbps is 1.5 MB for 180 s. The app should record AAC `.m4a`.
- Field name must be exactly `file`; anything else gets a pydantic 422 list.
- 8 s clip: `/identify-raga` 422 "need at least 10 seconds"; `/predict-audio` 422 with the *tonic*
  message (decode check is 5 s, while its message says "need at least 15 seconds").
- Empty or garbage bytes: 422 `"Could not decode audio: "` (exception text is empty).
- Codec sensitivity: `/identify-raga` on 180 s gave **Hindolam, p=0.995-0.997, gate would_accept
  true, tonic 138.8 Hz** for all five encodings. On 30 s the top-1 flipped with the codec
  (AAC files: Latangi p=0.13-0.22; PCM files: Mohanam p=0.125; gate false). `/predict-audio` was
  worse: on 30 s the essentia tonic came out 112.7 / 168.0 / 138.8 Hz depending on codec and top-1
  was Mohanam / Behag / Sencurutti; on 180 s it said Ritigaula or Natakurinji (p~0.12) for audio
  `/identify-raga` called Hindolam at 0.997.

## 3. Latency on this Mac (CPU) [M]

| Route | 30 s clip | 180 s clip | Heavy stages |
|---|---|---|---|
| `/identify-raga` | first call 10.7-12.6 s (loads the 138 MB bundle); warm median 1.9 s (1.3-3.8) | median 14.7 s (6.2-33.6) | essentia tonic + Melodia on the mix, up to 180 s. No Demucs, no ASR |
| `/predict-audio` | 28-181 s (Demucs 25-171 s) | 60-97 s (input trimmed to 60 s; Demucs 50-81 s) | Demucs htdemucs subprocess, then pyin |
| `/identify?fast=true` | 549 s (load average >100 at the time) | not run | openai-whisper large-v3-turbo, 4 language passes |
| `/identify` (stem pass) | not run (stopped: machine overloaded) | not run | whisper x4 + Demucs + whisper x3 |
| `/predict`, `/meaning` (cached), `/feedback`, `/health` | under 2 s | | none |

- Demucs runs under a hard `timeout=180` and a global semaphore of 1 [C]. A 30 s clip took 171 s
  here, so a 2-vCPU Space under any concurrency will turn `/predict-audio` and `/identify` into
  422s. Requests queue behind one Demucs job and one whisper lock (`_asr_lock`) [C].
- DEPLOY.md [D]: Space hardware "CPU basic is fine"; `/identify` "~2-4 min per 60 s clip with the
  stem pass, roughly half with `?fast=true`"; first `/identify` downloads whisper (~1.6 GB) into the
  container at request time (weights are not baked into the image). No deployed Space URL is
  recorded in the repo (`frontend/.env.example` holds a placeholder), so the live state is unknown.
- `URLSession`'s default `timeoutIntervalForRequest` is 60 s of idle time. Every `/predict-audio`
  and `/identify` call measured here would time out on a default session. `/identify-raga` fits.
- **App Review (Guideline 2.1) risk:** free HF Spaces hardware sleeps after a period of inactivity
  and the first request then waits for a container restart plus model loads (bundle 138 MB;
  whisper download on the first `/identify`). A reviewer who opens the app days after submission
  hits that path. Needs paid always-on hardware, or another host, plus a startup warm-up.
- Also [C]: `build_space.sh` copies neither `configs/raga_candidates.json` nor
  `data/overhaul/.../raga.joblib`, so **a Space built today serves 503 on `/identify-raga`**, the
  one route recommended for iOS.

## 4. Gaps for an iOS client

- **Auth:** none. Every route is anonymous [C]. Fine for v1 if abuse is bounded; App Attest is optional.
- **Rate limiting [C+M]:** slowapi, in-memory, per process, keyed on the *first* `X-Forwarded-For`
  value. A client can send its own `X-Forwarded-For` header; whether HF's proxy overwrites or appends
  it was not tested, so treat the limit as bypassable. 429 measured on the 3rd `/predict-audio`
  within a minute; rejected 415 calls count toward the limit. `/meaning`, `/tracks`, `/predict`
  have no limit, and `/meaning` on a cache miss makes a paid Gemini call (about 2,970 uncached titles;
  the cache resets when the Space rebuilds).
- **Upload size:** 30 MB, checked only after `await file.read()` has loaded the whole body into
  memory [C]. No limit at the ASGI or proxy level.
- **Timeouts:** server-side only the Demucs 180 s subprocess timeout; nothing bounds a whisper pass
  or the whole request [C]. No progress, no job id, no cancel.
- **CORS:** irrelevant for a native app (no `Origin`, not a browser). No change needed.
- **Versioning:** none. `/v1/health` returns 404 [M]; OpenAPI says `version: 1.0.0` but routes are bare.
- **Codable stability [M]:** OpenAPI declares no response schema for the audio routes (`{}`) and
  free-form objects elsewhere, so nothing can be generated. Hand-written Swift models are possible
  but: `/identify` changes keys by `clip_type`; `tonic` and `gate` are nullable; `/identify-raga`
  returns `candidates: []` and `signals: null` when it abstains; `model.path` and `gate.source` leak
  absolute server paths (`/Users/shyamravidath/...`) and `gate.status` is a prose sentence. Three
  error shapes (§1). Requirements pin `fastapi>=0.110` loosely.
- **Secrets:** the app needs none. Server-side: `GEMINI_API_KEY` (meaning cache misses), `HF_TOKEN`
  + `FEEDBACK_REPO` (feedback persistence). Nothing should ship in the binary.
- **HTTPS:** `*.hf.space` serves HTTPS with a public certificate, which satisfies App Transport
  Security. Never point the app at the local `http://127.0.0.1:8077`.
- **Privacy [C]:** `/identify` logs client IP, transcript and results to `queries.jsonl` and pushes
  it to a private HF dataset; `/feedback` logs IP. Audio temp files are deleted. This must appear in
  the privacy policy and the App Store privacy labels.

## 5. Recommended iOS v1 contract

Scope: raga candidates from a recording, plus cached meaning. `/identify` is out of v1 unless it
moves to async jobs: it takes minutes on CPU, beyond any interactive timeout.

```
GET  /v1/health  -> {status:"ok", api_version:"1", models:{raga:"context180"}, ready:bool}
POST /v1/raga    multipart: audio=<file>   (any content type; server sniffs bytes)
  200 -> {request_id:str, answered:bool, abstain_reason:str|null,
          candidates:[{raga:str, probability:double}],          // max 5, may be empty
          confident:bool,                                        // gate.would_accept; UI copy only
          tonic_hz:double|null, voiced_seconds:double, duration_seconds:double,
          model:{name:str, sha256:str}}
GET  /v1/meaning?title=<str>  -> {title, composer:str|null, meaning:str}   // cached rows only; 404 otherwise
POST /v1/feedback {request_id, verdict:"confirmed"|"rejected"|"not_in_catalog", chosen_raga?, user_raga?, user_title?}
     -> {status:"recorded"}
errors (all routes) -> {error:{code:"unsupported_audio"|"too_short"|"too_large"|"no_tonic"|"rate_limited"|"unavailable"|"internal",
                               message:str, retry_after_s:int|null}}
```
Client guidance: record AAC `.m4a`, mono, 44.1 or 48 kHz, 64-96 kbps; ask for 2-3 minutes (the
model's window is 180 s; on 30 s the top-1 changed with the codec and the gate never accepted);
minimum 10 s; set `timeoutIntervalForRequest` to 120 s.

### Ranked backend fixes before the app ships

| # | Fix | Why | Effort |
|---|---|---|---|
| 1 | Ship the reference candidate in the Space: copy `configs/raga_candidates.json` and the 138 MB bundle (LFS) in `build_space.sh`, make paths relative, test that `/identify-raga` returns 200, not 503 | the iOS route does not exist on a deployed Space today [C] | 0.5 day |
| 2 | Accept uploads by sniffing bytes (ffprobe or magic numbers), not by `Content-Type`; accept `audio/x-caf`, `application/octet-stream`, missing type | iOS-typical types get 415 on all three audio routes [M] | 0.5 day with tests |
| 3 | Always-on hosting for review: paid HF hardware (or other host), load the candidate at startup, `/v1/health` reports `ready` | Guideline 2.1; 10-13 s first-call load measured locally, plus a container restart after sleep | 0.5 day + monthly cost (Deepti's decision) |
| 4 | `/v1` router, pydantic response models, one error envelope (including 429 with `Retry-After`), strip `path`/`source`/prose `status`, check `openapi.json` into `docs/ios/` | Codable models and a stable contract [M] | 1 day |
| 5 | Body-size cap before reading into memory; per-request wall-clock timeout with a clean error | memory and hung requests [C] | 0.25 day |
| 6 | Rate limiting that does not trust a client-supplied `X-Forwarded-For`; add a limit to `/meaning`; serve only cached meanings to iOS (no live Gemini) | abuse and paid API exposure [C] | 0.5 day |
| 7 | `request_id` on `/v1/raga` plus feedback for raga results | the confirmation data flywheel only covers `/identify` today [C] | 0.5 day |
| 8 | Error-message fixes: "need at least 15 seconds" vs the 5 s check, empty `Could not decode audio: `, 8 s clip reported as a tonic failure | user-facing copy [M] | 0.25 day |
| 9 | If `/identify` stays in scope: async job API (`POST` returns `job_id`, `GET /v1/jobs/{id}`), whisper weights baked into the image, faster engine benchmarked on the host | 549 s measured for fast mode [M] | 2-3 days |
| 10 | Privacy policy text covering IP and transcript logging and the HF dataset | App Store privacy labels [C] | 0.25 day |
