# Carnatify — Handoff (updated 2026-06-30)

## Goal

A public Carnatic music identification website:
- **Frontend**: Next.js 14 on Vercel (`/` landing page, `/demo` with Saraga archive tab + Record Audio tab)
- **Backend**: FastAPI on HuggingFace Spaces Docker; runs Demucs vocal separation → pitch extraction → raga classification + composition matching; GEMINI_API_KEY lives server-side

---

## Current State

### What is live and working right now

| Thing | URL / location | Status |
|-------|---------------|--------|
| Backend | `https://shyamravidath-carnatify.hf.space` | ✅ Live |
| `/health` | GET → `{"status":"ok"}` | ✅ |
| `/tracks` | GET → 197 Saraga tracks | ✅ |
| `/predict` | POST `{track_id}` → raga + matches | ✅ |
| `/predict-audio` | POST multipart file → raga + matches + tonic + duration | ✅ Demucs confirmed running (verified 2026-06-30, see below) |
| `/meaning/{title}` | GET → composer + meaning | ✅ |
| Frontend | `https://carnatify.vercel.app` | ✅ Live |
| Saraga Archive tab | Track selector → Analyse → results panels | ✅ |
| Record Audio tab | Mic → waveform → Analyse → results panels | ✅ Wired to `/predict-audio` |
| Progress messages | "Uploading…" → "Separating vocals…" → "Analysing raga…" | ⚠️ In code, needs `npx vercel --prod` from `frontend/` |

### Branch
**`main`** — all recent work is here. `feature/website-backend-scraper` on remote is stale/behind.

### Recent commits
```
de74db1  Pin torch==2.5.1/torchaudio==2.5.1 to fix demucs audio save
7993ec5  Fix demucs flag: --model -> -n (htdemucs)
40119be  Add Demucs vocal separation to predict-audio; progress messages in frontend
ce6119b  Fix predict-audio: write temp file so ffmpeg decodes WebM/M4A/OGG
3d05f75  Add ffmpeg for WebM/OGG decoding; harden predict-audio error handling
```

---

## Files Actively Edited

| File | What changed |
|------|-------------|
| `backend/main.py` | Added `_separate_vocals_sync` + `predict_audio` endpoint |
| `backend/Dockerfile` | Added `ffmpeg`; pinned `torch==2.5.1 torchaudio==2.5.1` |
| `backend/requirements.txt` | Added `python-multipart`, `demucs>=4.0.0`; capped `torch<2.6` |
| `frontend/app/demo/page.tsx` | Two-tab UI, Record Audio tab, 24-bar waveform, wired to `/predict-audio` |
| `frontend/lib/api.ts` | Added `predictAudio(blob)` + `PredictResult` tonic/duration fields |

**HF Space**: `/tmp/hf-space/` is the assembled live copy (contains bundled `src/`, `models/`, `data/`). Its git remote points to HF. After editing `backend/main.py`, `backend/Dockerfile`, or `backend/requirements.txt`, mirror the change into `/tmp/hf-space/` and `git push` from there to trigger a rebuild.

---

## Everything That Failed (Don't Repeat)

| Attempt | What broke | Fix |
|---------|-----------|-----|
| `librosa.load(io.BytesIO(data))` for WebM/M4A/OGG | BytesIO path uses soundfile only — ffmpeg never invoked even with ffmpeg installed | Write bytes to `NamedTemporaryFile(suffix=suffix)` and pass the file path to librosa |
| Content-type without explicit suffix mapping | `.audio` fallback; ffmpeg picks wrong demuxer | Map `ogg/opus→.ogg`, `mp4/m4a→.m4a`, `webm→.webm`, `mpeg/mp3→.mp3`, `wav→.wav` |
| Demucs flag `--model htdemucs` | demucs 4.x uses `-n`/`--name`, not `--model`; argparse rejected it AND consumed the audio path as the unknown arg value | Changed to `-n htdemucs` |
| `torchaudio.save()` → `ImportError: TorchCodec required` | torchaudio 2.6+ switched `.save()` to torchcodec by default; demucs calls it internally | Pinned `torch==2.5.1 torchaudio==2.5.1`; capped `torch<2.6` in requirements.txt |
| FastAPI startup crash with `File(...)` | `python-multipart` not installed (FastAPI checks at import, not at request time) | Added `python-multipart>=0.0.9` to requirements.txt |
| Vercel not auto-deploying from git push | Vercel GitHub integration wasn't watching the feature branch | Run `npx vercel --prod` from `frontend/` — uploads local files directly |
| HF Space poll couldn't detect new container | HF does zero-downtime blue-green deploys — health endpoint stays 200 throughout | Test `/predict-audio` directly; response time >10s confirms new container |
| Agent prompt blocked by auto-classifier | HF git remote URL had the token embedded | Store token in `/tmp/hf-space/.git/config`; never embed in prompt text |
| `np.savez_compressed` with keys like `0_Dorakuna` | Python kwargs can't start with a digit | Store under `t0`…`tN` keys; record mapping in `tracks_meta.json` as `"key"` field |
| `@apply group` in `globals.css` | Tailwind `group` is a marker class, illegal in `@apply` | Add `group` directly to JSX className |

---

## Key Architecture Notes

### Demucs pipeline (predict-audio)
```
POST /predict-audio (multipart)
  → NamedTemporaryFile(suffix from Content-Type header)
  → librosa.load(tmp_path, duration=5.0)  ← fast validation check
  → asyncio run_in_executor → _separate_vocals_sync(tmp_path, demucs_dir)
      subprocess: python -m demucs --two-stems=vocals -n htdemucs -o demucs_dir tmp_path
      output:     demucs_dir/htdemucs/{stem}/vocals.wav
  → librosa.load(vocal_path, duration=60.0)
  → librosa.yin → tonic + frequencies
  → ThreadPoolExecutor: predict_raga + match_composition in parallel
  → return {raga, matches, tonic, duration}
  → finally: unlink tmp_path + rmtree(demucs_dir)
```

First request after container cold-start downloads htdemucs model (~80 MB) — allow ~3 min. Subsequent requests: ~65s for a 30s clip on CPU.

### Demucs verification (2026-06-30)

Investigated a suspicion that `/predict-audio` was skipping Demucs and silently
falling back to raw audio (based on a 38s response time for a 31s clip, vs. an
expected 60-120s for CPU Demucs). Conclusion: **Demucs is genuinely running.**
No code path falls back to raw audio on Demucs failure — `_separate_vocals_sync`
raises `RuntimeError` on subprocess failure or missing output, which the
endpoint converts to an `HTTPException(422)`; there was never a silent
fallback to look for.

Evidence gathered:
- Added a temporary `/debug` endpoint running `python -m demucs --help` inside
  the live container → `returncode: 0` with valid usage output. Demucs is
  installed and runnable. (Endpoint has since been removed — diagnostic only.)
- Repeated identical requests with the same 31s file returned **different**
  tonic values (239.24 / 239.47 / 240.22 / 239.83 Hz) and different top
  composition matches each time. A skip-Demucs path (deterministic YIN over
  the same raw waveform) would return byte-identical results every time; the
  variance is consistent with normal floating-point non-determinism in
  PyTorch CPU conv inference — i.e. the neural net is actually running.
- Response time scales with clip length: 16s clip → ~27s, 31s clip → ~38-52s
  (varies with container load/cache state, occasionally up to ~75s on a
  post-deploy cold container). A skipped-Demucs path would show flat ~2-5s
  overhead regardless of duration; the ~0.7s-per-audio-second scaling matches
  real separation work. The original "38s is too fast" assumption was simply
  an overly conservative baseline for this Space's CPU allocation.
- Added permanent `logger.info`/`logger.error` instrumentation around
  `_separate_vocals_sync` (start, elapsed time, returncode, stderr tail, and
  the resolved vocal path) so future regressions are visible in HF Space logs
  without needing to re-run this investigation.

### HF Space deploy
```bash
cp backend/main.py /tmp/hf-space/main.py     # mirror change
cd /tmp/hf-space
git add <files> && git commit -m "..." && git push
# code-only change: ~2 min rebuild; Dockerfile/requirements change: ~10 min
```

### Frontend deploy (Vercel does NOT auto-deploy from git push)
```bash
cd frontend && npx vercel --prod
# .vercel/project.json → projectId: prj_nsJUj8BBDJURSLy7zKP4baziYEtt
```

---

## Next Steps (in order)

1. **Deploy progress messages to Vercel** — the UX changes are in commit `40119be` but not live yet:
   ```bash
   cd frontend && npx vercel --prod
   ```

2. **Test Record Audio tab end-to-end** — go to `carnatify.vercel.app/demo`, switch to "Record Audio", record 30+ seconds, hit Analyse. Expect "Uploading…" → "Separating vocals…" → results after ~65s.

3. **Generate more meanings** — only 8 cached. When Gemini quota resets:
   ```bash
   GEMINI_API_KEY=<key> python generate_meanings.py 100
   ```

4. **Clean up stale branch** — delete `origin/feature/website-backend-scraper` or open a PR documenting the work.

---

## Separate Task: Research Figures for Srihith

Shyam (Slack, 2026-06-30): *"I think we have to include OOD performance degradation, calibration curves comparison (conformal vs quantile vs MC), decision-value improvement vs k, and possibly a cell-type OOD breakdown."*

Need **2 more figures** in the same visual style as the first set (get old image for reference). Candidate panels:

1. **OOD performance degradation** — accuracy vs. distribution shift across held-out cell types
2. **Calibration curves comparison** — conformal prediction vs. quantile regression vs. MC dropout
3. **Decision-value improvement vs. k** — sweep k, show value of top-k over top-1
4. **Cell-type OOD breakdown** *(possibly)* — per-cell-type breakdown table/chart

**Before starting**: get the old image for style reference + the results/data files. Confirm which 2 panels are priority with Shyam/Srihith.
