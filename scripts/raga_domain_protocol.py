"""Domain decomposition, stage 1 — corpus, frozen tier, inherited windows, and
the resolution of every tier track back to its SOURCE AUDIO. Nothing is scored
here and no model is fitted.

The duration curve only ever sliced a cached contour. This job has to re-run
melodia on freshly degraded audio, so it needs the audio file behind each of the
518 tier tracks — archive mp3s under `data/concert_audio/<raga>/<stem>.mp3`,
Saraga tracks via `mirdata`'s `track.audio_path`.

Everything else is read straight out of `data/raga_duration/protocol.json` and
is NOT re-derived: the 18-raga `min_tracks >= 25` tier, the 518 tracks, the 155
level-(c) source-disjoint groups, and the seeded 60 s window offsets. This job
takes **one** window per track — `offsets[0]`, the duration curve's own first
seeded offset — per `data/raga_domain/PREREGISTRATION.md` §1.

Writes `data/raga_domain/protocol.json` (inventory + audio paths, no features,
no scores).

Read-only. Nothing under `models/` is written.

Usage: venv/bin/python scripts/raga_domain_protocol.py
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DUR_DIR = ROOT / 'data' / 'raga_duration'
OUT_DIR = ROOT / 'data' / 'raga_domain'
AUDIO_DIR = ROOT / 'data' / 'concert_audio'
AUDIO_EXTS = ('.mp3', '.m4a', '.wav', '.flac')

WINDOW_S = 60.0
OFFSET_IX = 0          # the duration curve's FIRST seeded offset; K = 1 here


def saraga_audio_paths():
    import mirdata
    saraga = mirdata.initialize('saraga_carnatic', data_home=str(ROOT))
    return {tid: saraga.track(tid).audio_path for tid in saraga.track_ids}


def archive_audio_path(stem: str) -> str | None:
    """`archive__<raga dir>__<file stem>` -> data/concert_audio/<raga>/<stem>.*"""
    assert stem.startswith('archive__'), stem
    raga, _, base = stem[len('archive__'):].partition('__')
    d = AUDIO_DIR / raga
    if not d.is_dir():
        return None
    for p in sorted(d.glob(base + '.*')):
        if p.suffix.lower() in AUDIO_EXTS:
            return str(p)
    return None


def window_for(rec: dict) -> tuple[int, int, float]:
    """Raw-frame [start, stop) and start in seconds, in `raga_duration_windows.plan`
    arithmetic verbatim. Trap 1: the slice is on the TIME axis; the voiced filter
    is applied afterwards, so the voiced-frame count is an outcome, not an input."""
    n_raw, hop = rec['n_raw'], rec['hop']
    need = int(round(WINDOW_S / hop))
    assert n_raw > need, f"{rec['stem']} shorter than the window"
    room = n_raw - need
    a = int(round(rec['offsets'][OFFSET_IX] * room))
    return a, a + need, a * hop


def main() -> None:
    proto = json.loads((DUR_DIR / 'protocol.json').read_text())
    recs = proto['tracks']
    print(f"inherited: {proto['tier_n_tracks']} tier tracks, "
          f"{proto['level_c_groups']} level-(c) groups, "
          f"{len(proto['tier_ragas'])} ragas", flush=True)

    sar = saraga_audio_paths()
    out, missing = [], []
    for rec in recs:
        if rec['src'] == 'archive_v3':
            ap = archive_audio_path(rec['stem'])
        else:
            key = rec['tid'].replace('saraga__', '')
            ap = sar.get(key, sar.get(rec['tid']))
        if not ap or not os.path.exists(ap):
            missing.append(rec['stem'])
            continue
        a, b, start_s = window_for(rec)
        out.append(dict(stem=rec['stem'], tid=rec['tid'], src=rec['src'],
                        raga=rec['raga'], group_c=rec['group_c'],
                        tonic_ref=rec['tonic'], hop=rec['hop'],
                        n_raw=rec['n_raw'], audio=ap,
                        win_start_frame=a, win_stop_frame=b,
                        win_start_s=float(start_s), win_s=WINDOW_S))

    print(f'resolved audio for {len(out)}/{len(recs)} tier tracks', flush=True)
    if missing:
        print(f'  MISSING ({len(missing)}): {missing[:10]}', flush=True)
    print('  by source:', dict(Counter(r['src'] for r in out)), flush=True)
    print('  by raga  :', dict(sorted(Counter(r['raga'] for r in out).items())), flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / 'protocol.json').write_text(json.dumps(dict(
        inherited_from='data/raga_duration/protocol.json',
        tier_ragas=proto['tier_ragas'], tier_n_tracks=proto['tier_n_tracks'],
        level_c_groups=proto['level_c_groups'], group_notes=proto['group_notes'],
        window_s=WINDOW_S, offset_index=OFFSET_IX, k_windows=1,
        n_resolved=len(out), n_missing=len(missing), missing=missing,
        tracks=out), ensure_ascii=False, indent=1))
    print(f"\nwrote {OUT_DIR / 'protocol.json'}")


if __name__ == '__main__':
    main()
