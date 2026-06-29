#!/usr/bin/env bash
# Assemble a self-contained HuggingFace Space from the parent project.
# Copies the carnatify package, trained models, and lyrics DB into backend/
# so the Docker build context (the Space repo) needs nothing outside itself.
#
# Run from the repo root:  ./backend/build_space.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

echo "Assembling Space in $HERE …"

rm -rf "$HERE/src" "$HERE/models"
cp -r "$ROOT/src" "$HERE/src"
cp -r "$ROOT/models" "$HERE/models"
mkdir -p "$HERE/data"
cp "$ROOT/data/lyrics.db" "$HERE/data/lyrics.db"

# Drop compiled caches so they don't bloat the image.
find "$HERE/src" -name "__pycache__" -type d -prune -exec rm -rf {} +

if [[ ! -f "$HERE/data/tracks_pitch.npz" ]]; then
  echo "WARNING: data/tracks_pitch.npz missing — run:"
  echo "  python backend/precompute_tracks.py --data-home ."
fi

echo "Done. Space contents:"
ls -1 "$HERE"
