# Deploying Carnatify

Two independent deploys: the **backend** (FastAPI → HuggingFace Spaces, Docker SDK)
and the **frontend** (Next.js → Vercel). The Anthropic API key lives only on the
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
| `ANTHROPIC_API_KEY` | secret   | your Anthropic key (enables `/meaning`) |
| `FRONTEND_ORIGIN`   | variable | your Vercel URL, e.g. `https://carnatify.vercel.app` |

The Space rebuilds on push. Verify: `curl https://<user>-carnatify-api.hf.space/health`.

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
- The Anthropic key is **never** referenced in `frontend/` — meaning generation
  happens server-side in `/meaning`.
- `/meaning` generates on demand and caches into `data/lyrics.db`. On an
  ephemeral Space filesystem the cache resets on rebuild; that's fine for a demo.
- Nothing in `src/carnatify/`, `models/`, or `app.py` was modified — the website
  is purely additive (`backend/`, `frontend/`).
