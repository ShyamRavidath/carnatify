# Chromaprint: local recording-copy audit only

Upstream: https://github.com/acoustid/chromaprint

- Version: 1.5.1, commit `5c3be6803856f25b11d1d704bac56e733b4fc997`.
- Source archive SHA256: `b134542bf50af0106c73b701a9b0cd876b15de3fba8e064f8fe36bedfb3a8351`.
- Local ARM64 library SHA256: `cd6276fc1dadd7e6d02ed0b63c392980fa7844cb3f6b03d82c01d9deb2f677fc`.
- Source and upstream license are retained under `data/overhaul/chromaprint/source`.
- Upstream describes its own code as MIT and the combined project, including
  bundled FFmpeg code, as LGPL 2.1. Do not describe the whole library as MIT.
  See [upstream license](https://github.com/acoustid/chromaprint/blob/v1.5.1/LICENSE.md)
  and [LGPL 2.1](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html).

This is a repository-local research/audit build, not a bundled application
dependency, deployment, or binary redistribution. It uses Apple's vDSP FFT,
not GPL FFTW. `otool -L` shows the local library depends on libSystem,
Accelerate and libc++. Distribution obligations require a separate review if
this becomes a shipped component.

## Reproduction

The downloader pins the source checksum and rejects unexpected archive paths
and special entries. The one upstream header symlink is materialized from its
audited internal regular-file target, not installed as a symlink.

```sh
venv_train/bin/python scripts/fetch_chromaprint_source.py
venv_train/bin/python -m pip install --no-deps --target data/overhaul/build_deps cmake==3.31.6
data/overhaul/build_deps/cmake/data/bin/cmake -S data/overhaul/chromaprint/source -B data/overhaul/chromaprint/build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF -DBUILD_TOOLS=OFF -DFFT_LIB=vdsp
data/overhaul/build_deps/cmake/data/bin/cmake --build data/overhaul/chromaprint/build --parallel 2
```

Compiler used: AppleClang 21.0.0.21000101. Build warns about an upstream
randomized matcher's integer-to-float conversion. That matcher is not called;
the wrapper exposes deterministic raw fingerprint extraction only. Native
context allocation, return codes, output ownership and cleanup are checked.
Every wrapper instance verifies its supplied library checksum before loading.

Chromaprint targets near-identical recording identification, not composition
identity across performances and not raga recognition. Candidate fingerprint
matches require independent verification; absence of flags is not proof of
recording or artist independence.
