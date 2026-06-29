---
title: Carnatify API
emoji: 🎼
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# Carnatify API

FastAPI backend for [Carnatify](https://github.com/) — a Carnatic music
identifier. Drives the project's raga classifier, composition matcher, and
lyrics/meaning catalog over HTTP.

## Endpoints

| Method | Path                | Description                                              |
|--------|---------------------|----------------------------------------------------------|
| GET    | `/health`           | Liveness check → `{"status":"ok"}`                       |
| GET    | `/tracks`           | All 197 demo tracks → `[{track_id,title,raga,tonic}]`    |
| POST   | `/predict`          | Body `{track_id}` → `{raga:[…], matches:[…]}`            |
| GET    | `/meaning/{title}`  | Lyrics meaning → `{title, composer, meaning}`            |

Pitch contours are precomputed into `data/tracks_pitch.npz`, so neither mirdata
nor the raw Saraga dataset is needed at runtime.

## Configuration (Space secrets / variables)

- `ANTHROPIC_API_KEY` — **secret**, required for `/meaning`. Server-side only.
- `FRONTEND_ORIGIN` — variable, the deployed frontend URL for CORS (e.g.
  `https://carnatify.vercel.app`). Defaults to `*` if unset.

## Deploying

This folder is the Space. Before pushing, run `./build_space.sh` from the parent
project to copy `src/`, `models/`, and `data/lyrics.db` into it (see
`../DEPLOY.md`), then push to the Space's git remote.
