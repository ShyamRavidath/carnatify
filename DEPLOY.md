# Deploying Carnatify

Two independent deploys: the **backend** (FastAPI → HuggingFace Spaces, Docker SDK)
and the **frontend** (Next.js → Vercel). The Gemini API key lives only on the
backend; the frontend only knows the backend's public URL.

```
backend/   →  HuggingFace Space (Docker)   →  https://<user>-carnatify-api.hf.space
frontend/  →  Vercel                        →  https://carnatify.vercel.app
```

---

## 1. Backend → HuggingFace Spaces

### a. One-time local prep
From the repo root, generate the pitch bundle (needs the Saraga dataset +
`mirdata` locally — already present in this project), then assemble the
self-contained Space folder:

```bash
python backend/precompute_tracks.py --data-home .   # writes backend/data/tracks_pitch.npz
./backend/build_space.sh                            # copies src/, models/, data/lyrics.db into backend/
```

After `build_space.sh`, `backend/` contains everything the image needs:
`main.py`, `Dockerfile`, `requirements.txt`, `README.md`, `src/`, `models/`,
and `data/` (`tracks_pitch.npz`, `tracks_meta.json`, `lyrics.db`).

### b. Create the Space
1. New Space → **SDK: Docker**, hardware: CPU basic is fine.
2. Push the **contents of `backend/`** to the Space repo root (the `README.md`
   header already declares `sdk: docker` and `app_port: 7860`):

```bash
git clone https://huggingface.co/spaces/<user>/carnatify-api
cp -r backend/* backend/.dockerignore carnatify-api/   # everything assembled above
cd carnatify-api && git add -A && git commit -m "Carnatify API" && git push
```

> `models/` (~28 MB) and `data/tracks_pitch.npz` (~19 MB) exceed plain-git
> comfort — enable Git LFS in the Space for `*.pkl`, `*.npz`, `*.db` if pushes
> are slow: `git lfs track "*.pkl" "*.npz" "*.db"`.

### c. Space settings → Variables and secrets
| Name                | Kind     | Value                                   |
|---------------------|----------|-----------------------------------------|
| `GEMINI_API_KEY`    | secret   | your Google Gemini key (enables `/meaning`) |
| `FRONTEND_ORIGIN`   | variable | your Vercel URL, e.g. `https://carnatify.vercel.app` |
| `HF_TOKEN`          | secret   | write-scoped token (enables feedback persistence) |
| `FEEDBACK_REPO`     | variable | private dataset repo, e.g. `<user>/carnatify-feedback` |

The Space rebuilds on push. Verify: `curl https://<user>-carnatify-api.hf.space/health`.

### d. Clip identification (`/identify` + `/feedback`)
The lyrics-first clip ID pipeline (wild-clip validated: comp top-1 4/10,
top-5 6/10, zero bluffs — see HANDOFF_CLIP_ID.md scoreboard lineage):

```
POST /identify           multipart file upload; ?fast=true skips demucs stem pass
POST /feedback           {query_id, verdict: confirmed|rejected|not_in_catalog,
                          chosen_title?, user_title?, user_raga?}
```

- First `/identify` call downloads whisper large-v3-turbo (~1.6 GB) into the
  container; expect a slow cold start. Latency on CPU basic: ~2-4 min per
  60s clip with the stem pass, roughly half with `?fast=true`.
- `verdict` events are the data flywheel: create the private dataset repo
  BEFORE going live (`huggingface-cli repo create carnatify-feedback
  --type dataset --private`), set `HF_TOKEN` + `FEEDBACK_REPO`, and every
  query/confirmation survives Space restarts as `logs/*.jsonl` there.
- UI contract: always render top-5 with `composition_confidence`; when
  `clip_type` is `no_lyrics`, show `message` and the raga list labelled
  low-confidence — never present raga as certain.

---

## 2. Frontend → Vercel

1. Import the repo in Vercel; set **Root Directory = `frontend`**. Framework
   auto-detects as Next.js (build `next build`, no extra config).
2. **Environment Variables**:

| Name                   | Value                                            |
|------------------------|--------------------------------------------------|
| `NEXT_PUBLIC_API_BASE` | `https://<user>-carnatify-api.hf.space`          |

3. Deploy. After the first deploy, copy the Vercel URL back into the Space's
   `FRONTEND_ORIGIN` variable so CORS allows it.

### Local development
```bash
# terminal 1 — backend
source venv/bin/activate
cd backend && uvicorn main:app --port 8077

# terminal 2 — frontend (defaults to http://127.0.0.1:8077 if API base unset)
cd frontend && npm install && npm run dev
```

---

## Notes
- The Gemini key is **never** referenced in `frontend/` — meaning generation
  happens server-side in `/meaning`.
- `/meaning` generates on demand and caches into `data/lyrics.db`. On an
  ephemeral Space filesystem the cache resets on rebuild; that's fine for a demo.
- Nothing in `src/carnatify/`, `models/`, or `app.py` was modified — the website
  is purely additive (`backend/`, `frontend/`).
