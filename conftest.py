"""Put `src/` on `sys.path` so the whole test suite is runnable.

Six test files (`test_audio`, `test_composition`, `test_lyrics`, `test_pipeline`,
`test_raga`, `test_tala`) import the `carnatify` package. Every handoff since
2026-07 has said "**NEVER run bare `pytest tests/`** — six legacy files import a
`carnatify` package that does not exist and fail at collection", and told the
reader to run four named files instead.

**The package does exist**, at `src/carnatify/`. It was never missing; `src/`
was simply not on the path and the repo has no `pyproject.toml` or editable
install to put it there. The diagnosis in the handoffs was wrong and it cost
about 95 tests' worth of coverage that nobody had run for weeks.

With this file, `pytest tests/` collects everything. See `handoff.md` §2g for
the two remaining real problems it exposes, neither of which this file hides:

  * `tests/test_lyrics.py` needs `bs4`, which is not installed in `venv_train`.
  * `tests/test_audio.py::TestFeatureExtractor::test_extract_on_sine_wave`
    genuinely fails — `TonicIndianArtMusic` returns 110.13 Hz for a 440 Hz sine,
    two octaves low.

Neither is silenced here. A failing test is more useful than a hidden one.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / 'src'
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
