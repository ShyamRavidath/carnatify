"""Wild raga measurement, stage 1 — the gates. Nothing is predicted here.

Three things, all of which must be reported *before* any accuracy figure exists
(`WORKHORSE_RAGA_WILD_BRIEF.md` §"Two things that must be checked"):

  1. **Hash gate.** Every clip in the FROZEN, COMMITTED
     `data/raga_wild/FROZEN_CLIPS.json` is re-hashed on disk (sha256 + byte
     length) against the frozen record. Any mismatch is a blocker, not a
     footnote. Selection is closed: this stage can only *fail* the set, never
     change it.
  2. **Label table.** The 29 `(file, raga_label, raga_canonical)` rows are
     emitted verbatim so a musician can read them. The labels come from the
     filename convention `<title>__<raga>.<ext>` and have never been audited.
  3. **Source-disjointness against the training corpus.** Two independent
     checks, both reported:
       * **audio hash** — sha256 of every training audio file
         (`data/concert_audio/**` for the archive half,
         `saraga1.5_carnatic/**` for the Saraga half) against the 29. Byte
         length is hashed first as an exact prefilter: byte-identity implies
         equal length, so a size join is a *complete* screen for the failure
         mode that bit the Qmax audit (34/36 hits byte-identical copies). The
         full hash is computed anyway so the statement is unconditional.
       * **archive item / title / artist** — the recoverable identity of each
         clip is folded and joined against `data/qmax_audit/provenance.json`
         (1232 training rows carrying `archive_identifier`, `title_stem`,
         `raga_dir`, `artist`). `~/sung_tests/fetch_manifest.tsv` carries the
         source URL and window for the auto-fetched clips, which is the
         strongest identity evidence available for them.
     A *work* match (same composition, different performance) is reported
     separately from a *recording* match. Only the second is contamination.

  4. **Window inventory.** Each clip's real duration, and for clips longer than
     60 s the seeded-offset 60 s window, using the duration curve's own
     convention: `np.random.default_rng(42)`, `K = 3` fractions drawn per clip
     in sorted-filename order, offset index 0, `start = round(u0 * (dur - 60))`
     (`scripts/raga_duration_protocol.py:offset_fractions/window_plan`,
     `data/raga_domain/protocol.json:offset_index`).

Read-only. Writes `data/raga_wild/protocol.json` only.

Usage: venv/bin/python scripts/raga_wild_protocol.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT_DIR = ROOT / 'data' / 'raga_wild'
CLIPS_DIR = Path.home() / 'sung_tests'
FROZEN = OUT_DIR / 'FROZEN_CLIPS.json'
PROVENANCE = ROOT / 'data' / 'qmax_audit' / 'provenance.json'
FETCH_MANIFEST = CLIPS_DIR / 'fetch_manifest.tsv'
TRAIN_AUDIO_DIRS = (ROOT / 'data' / 'concert_audio', ROOT / 'saraga1.5_carnatic')
AUDIO_EXT = {'.mp3', '.m4a', '.wav', '.flac', '.ogg', '.mp4'}
FFPROBE = '/opt/homebrew/bin/ffprobe'

WINDOW_S = 60.0
SEED = 42
K_WINDOWS = 3
OFFSET_INDEX = 0


def fold(s: str) -> str:
    d = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())


def sha256_file(p: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------- gate 1 --
def hash_gate(frozen: dict) -> list[dict]:
    rows = []
    for c in frozen['clips']:
        p = CLIPS_DIR / c['file']
        r = dict(file=c['file'], present=p.exists(), size_ok=None, sha_ok=None,
                 sha256_disk=None, bytes_disk=None)
        if p.exists():
            b = p.stat().st_size
            h = sha256_file(p)
            r.update(bytes_disk=int(b), sha256_disk=h,
                     size_ok=bool(b == c['bytes']), sha_ok=bool(h == c['sha256']))
        rows.append(r)
    return rows


# ------------------------------------------------------------------- gate 4 --
def probe(p: Path) -> dict:
    r = subprocess.run([FFPROBE, '-v', 'error', '-show_entries',
                        'format=duration,bit_rate:stream=codec_name,sample_rate,channels',
                        '-of', 'json', str(p)], capture_output=True, text=True)
    if r.returncode != 0:
        return dict(readable=False, error=r.stderr.strip()[-200:])
    j = json.loads(r.stdout)
    fmt, st = j.get('format', {}), (j.get('streams') or [{}])[0]
    return dict(readable=True, duration_s=float(fmt.get('duration', 0.0)),
                bit_rate=int(fmt.get('bit_rate', 0) or 0),
                codec=st.get('codec_name'), sr=int(st.get('sample_rate', 0) or 0),
                channels=int(st.get('channels', 0) or 0))


def window_plan(frozen: dict, durations: dict[str, float]) -> dict[str, list[dict]]:
    """Duration-curve convention, verbatim in structure: one rng, K fractions per
    clip, clips visited in sorted-filename order, offset index 0 used."""
    rng = np.random.default_rng(SEED)
    fracs = {c['file']: rng.random(K_WINDOWS)
             for c in sorted(frozen['clips'], key=lambda c: c['file'])}
    plan = {}
    for c in frozen['clips']:
        f = c['file']
        d = durations.get(f, 0.0)
        wins = [dict(kind='whole', start_s=0.0, dur_s=float(d))]
        if d > WINDOW_S:
            room = d - WINDOW_S
            u0 = float(fracs[f][OFFSET_INDEX])
            wins.append(dict(kind='w60', start_s=round(u0 * room, 6),
                             dur_s=WINDOW_S, offset_frac=u0))
        plan[f] = wins
    return plan


# ------------------------------------------------------------------- gate 3 --
def train_audio_files() -> list[Path]:
    out = []
    for d in TRAIN_AUDIO_DIRS:
        if not d.exists():
            continue
        out += [p for p in d.rglob('*') if p.is_file() and p.suffix.lower() in AUDIO_EXT]
    return sorted(out)


def hash_disjointness(clip_rows: list[dict]) -> dict:
    want_size = {r['bytes_disk']: r['file'] for r in clip_rows if r['bytes_disk']}
    want_sha = {r['sha256_disk']: r['file'] for r in clip_rows if r['sha256_disk']}
    files = train_audio_files()
    size_hits, sha_hits = [], []
    n_hashed = 0
    for p in files:
        b = p.stat().st_size
        if b in want_size:
            size_hits.append(dict(clip=want_size[b], train=str(p.relative_to(ROOT)),
                                  bytes=int(b)))
        h = sha256_file(p)
        n_hashed += 1
        if h in want_sha:
            sha_hits.append(dict(clip=want_sha[h], train=str(p.relative_to(ROOT)),
                                 sha256=h))
    return dict(n_train_files=len(files), n_hashed=n_hashed,
                size_collisions=size_hits, sha256_collisions=sha_hits)


def fetch_manifest() -> dict[str, dict]:
    out = {}
    if not FETCH_MANIFEST.exists():
        return out
    for line in FETCH_MANIFEST.read_text(errors='replace').splitlines():
        parts = line.split('\t')
        if not parts or not parts[0].strip():
            continue
        rec = dict(video_title=parts[1].strip() if len(parts) > 1 else None,
                   url=None, window=parts[3].strip() if len(parts) > 3 else None,
                   raw=line)
        m = re.search(r'https?://\S+', line)
        if m:
            rec['url'] = m.group(0).rstrip('|').strip()
        out[parts[0].strip()] = rec
    return out


def identity_disjointness(frozen: dict) -> list[dict]:
    prov = json.loads(PROVENANCE.read_text())
    by_title = {}
    for r in prov:
        by_title.setdefault(fold(r.get('title_stem') or ''), []).append(r)
    fm = fetch_manifest()
    rows = []
    for c in frozen['clips']:
        tf = fold(c['title'])
        cand = list(by_title.get(tf, []))
        # substring join both ways so "vAtApi gaNapathim" meets "vatapiganapatim"
        if not cand:
            for k, v in by_title.items():
                if k and (k in tf or tf in k) and min(len(k), len(tf)) >= 8:
                    cand += v
        work = [dict(train_stem=r['stem'], archive_identifier=r.get('archive_identifier'),
                     raga_dir=r.get('raga_dir'), artist=r.get('artist'),
                     audio_path=r.get('audio_path'), audio_size=r.get('audio_size'),
                     same_raga=bool(fold(r.get('raga_dir') or '') ==
                                    fold(c['raga_canonical'])))
                for r in cand]
        src = fm.get(c['file'])
        rows.append(dict(file=c['file'], title=c['title'],
                         raga_canonical=c['raga_canonical'],
                         fetch_source=src, n_work_matches=len(work),
                         work_matches=work))
    return rows


def main() -> None:
    frozen = json.loads(FROZEN.read_text())
    print(f"FROZEN_CLIPS.json: n={frozen['n']}, {len(frozen['clips'])} rows, "
          f"{len(frozen['tier'])} tier ragas", flush=True)
    assert frozen['n'] == len(frozen['clips']), 'frozen n disagrees with rows'

    print('\n== GATE 1: sha256 of every frozen clip', flush=True)
    hg = hash_gate(frozen)
    bad = [r for r in hg if not (r['present'] and r['sha_ok'] and r['size_ok'])]
    for r in hg:
        flag = 'OK ' if (r['present'] and r['sha_ok'] and r['size_ok']) else 'BAD'
        print(f"  {flag} {r['file']}", flush=True)
    print(f"  -> {len(hg) - len(bad)}/{len(hg)} verified, {len(bad)} mismatch", flush=True)

    print('\n== LABEL TABLE (unaudited filename labels)', flush=True)
    for c in frozen['clips']:
        print(f"  {c['file']:<48} | {c['raga_label']:<18} | {c['raga_canonical']}",
              flush=True)

    print('\n== GATE 4: readability + duration + window plan', flush=True)
    probes, durs = {}, {}
    for c in frozen['clips']:
        p = probe(CLIPS_DIR / c['file'])
        probes[c['file']] = p
        durs[c['file']] = p.get('duration_s', 0.0)
        print(f"  {p.get('duration_s', 0.0):7.1f}s  {p.get('codec')}  "
              f"{p.get('sr')}Hz  {c['file']}", flush=True)
    plan = window_plan(frozen, durs)
    n_long = sum(1 for f in plan if len(plan[f]) > 1)
    print(f"  -> {n_long} clips longer than {WINDOW_S:.0f}s get a seeded 60s window "
          f"as well as the whole clip; {len(plan) - n_long} score whole-clip only",
          flush=True)

    print('\n== GATE 3a: audio-hash disjointness against the training corpus',
          flush=True)
    hd = hash_disjointness(hg)
    print(f"  {hd['n_train_files']} training audio files hashed", flush=True)
    print(f"  byte-length collisions: {len(hd['size_collisions'])}", flush=True)
    for r in hd['size_collisions']:
        print(f"    {r['clip']}  <->  {r['train']}  ({r['bytes']} B)", flush=True)
    print(f"  sha256 collisions: {len(hd['sha256_collisions'])}", flush=True)
    for r in hd['sha256_collisions']:
        print(f"    CONTAMINATION {r['clip']}  <->  {r['train']}", flush=True)

    print('\n== GATE 3b: identity join against data/qmax_audit/provenance.json',
          flush=True)
    idr = identity_disjointness(frozen)
    for r in idr:
        src = r['fetch_source']
        u = (src or {}).get('url')
        print(f"  {r['file']:<48} work-matches {r['n_work_matches']:2d}  "
              f"source {'youtube:' + u.split('=')[-1] if u else 'unknown'}", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = dict(frozen_n=frozen['n'], tier=frozen['tier'],
               hash_gate=hg, n_hash_bad=len(bad),
               labels=[dict(file=c['file'], raga_label=c['raga_label'],
                            raga_canonical=c['raga_canonical'],
                            ooc_marked=c['ooc_marked']) for c in frozen['clips']],
               probes=probes, window_plan=plan,
               window_s=WINDOW_S, seed=SEED, k_windows=K_WINDOWS,
               offset_index=OFFSET_INDEX,
               hash_disjointness=hd, identity_disjointness=idr)
    (OUT_DIR / 'protocol.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\nwrote {OUT_DIR / 'protocol.json'}")
    if bad:
        print('BLOCKER: hash gate failed', file=sys.stderr)


if __name__ == '__main__':
    main()
