#!/usr/bin/env bash
# Assemble backend/ and push it to the HuggingFace Space in one step.
# Owner-run (deploys are not automated). Needs a write token in
# ~/.cache/huggingface/token (already present on Deepti's Mac).
#
# Run from the repo root:  ./backend/deploy_space.sh
# Then watch the build:    https://huggingface.co/spaces/shyamravidath/carnatify
set -euo pipefail

SPACE="${SPACE:-shyamravidath/carnatify}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PY="${PY:-$ROOT/venv_train/bin/python}"

"$HERE/build_space.sh"

# upload_folder stores large files (the 138 MB raga.joblib) via LFS/Xet
# automatically; no git clone or `git lfs track` needed.
"$PY" - "$HERE" "$SPACE" <<'PY'
import sys
from huggingface_hub import HfApi

folder, space = sys.argv[1], sys.argv[2]
info = HfApi().upload_folder(
    folder_path=folder,
    repo_id=space,
    repo_type="space",
    commit_message="Deploy Carnatify API (iOS v1 raga route)",
    ignore_patterns=["**/__pycache__/**", "*.pyc", "data/feedback/**", ".DS_Store"],
    # stale bytecode from the July deploy
    delete_patterns=["__pycache__/**", "*.pyc"],
)
print("pushed:", info)
PY

echo "Space rebuilds now (5-15 min). Check: curl https://${SPACE/\//-}.hf.space/health"
