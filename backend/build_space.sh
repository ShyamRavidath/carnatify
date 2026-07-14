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
mkdir -p "$HERE/models"
# only the models the API actually loads — raga_clip_rf.pkl (1.1 GB) and the
# raga_v3 candidates must NOT enter the image
for f in raga_classifier.pkl raga_label_encoder.pkl composition_catalog.npz \
         composition_catalog_meta.json qmax_catalog_meta.json; do
  cp "$ROOT/models/$f" "$HERE/models/$f"
done
mkdir -p "$HERE/data"
cp "$ROOT/data/lyrics.db" "$HERE/data/lyrics.db"
cp "$ROOT/data/composition_registry.json" "$HERE/data/composition_registry.json"
# full-lyrics matcher channel (identify_clip degrades gracefully without it,
# but the Space must match local accuracy)
cp "$ROOT/data/karnatik_lyrics.json" "$HERE/data/karnatik_lyrics.json"
# clip identification: matcher lives in identify_clip.py (single source of
# truth), served by clip_identify.py
cp "$ROOT/identify_clip.py" "$HERE/identify_clip.py"

# Drop compiled caches so they don't bloat the image.
find "$HERE/src" -name "__pycache__" -type d -prune -exec rm -rf {} +

if [[ ! -f "$HERE/data/tracks_pitch.npz" ]]; then
  echo "WARNING: data/tracks_pitch.npz missing — run:"
  echo "  python backend/precompute_tracks.py --data-home ."
fi

echo "Done. Space contents:"
ls -1 "$HERE"
