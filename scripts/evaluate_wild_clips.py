"""Frozen wild clips, whole clip, through raga_runtime. No tuning, no window search.

Implements data/overhaul/WILD_PREREG.md. Re-hashes every frozen clip, applies
Deepti's 2026-08-13 label corrections, scores the whole clip once with the
named candidate and the registered gate, and reports the 27-clip primary
read-out with Wilson intervals beside the OOV rows.

Usage:
  venv_train/bin/python scripts/evaluate_wild_clips.py --model context180 \
      --gate data/overhaul/context180_recovered_experiment/gate.json \
      --out data/overhaul/context180_recovered_experiment/wild27.json
"""
from __future__ import annotations
import argparse, json, math, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import soundfile as sf
from normalize_ragas import fold
from scripts.raga_pipeline import sha, write_json
from scripts.raga_wild_relabel import CORRECTIONS
from carnatify.ml.raga_runtime import RagaCandidate, RagaGate, identify_raga

CLIPS = ROOT / 'data/raga_wild/FROZEN_CLIPS.json'
CLIP_DIR = Path.home() / 'sung_tests'
CACHE = ROOT / 'data/overhaul/cache/wild/queries'
DECODED = ROOT / 'data/overhaul/cache/wild/decoded'


def decodable(path, digest):
    """libsndfile cannot open the m4a clips; transcode those once to float PCM WAV.

    The frozen SHA256 of the original file stays the query identity. The WAV
    is a deterministic FFmpeg decode at native rate and channels, nothing else.
    """
    try:
        sf.info(str(path))
        return path, 'libsndfile'
    except Exception:
        DECODED.mkdir(parents=True, exist_ok=True)
        wav = DECODED / f'{digest}.wav'
        if not wav.exists():
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-vn', '-acodec', 'pcm_f32le', str(wav)],
                           check=True)
        return wav, 'ffmpeg_pcm_f32le'


def wilson(k, n, z=1.959963985):
    if n == 0: return [0., 0.]
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0., c - h), min(1., c + h)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', default='context180')
    ap.add_argument('--gate', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    started = time.monotonic()
    frozen = json.loads(CLIPS.read_text())
    candidate = RagaCandidate.load(a.model)
    gate = RagaGate.load(a.gate)
    class_keys = {fold(c) for c in candidate.classes}
    rows = []
    for clip in frozen['clips']:
        path = CLIP_DIR / clip['file']
        digest = sha(path)
        if digest != clip['sha256'] or path.stat().st_size != clip['bytes']:
            raise SystemExit(f'Gate 1 FAIL: frozen clip changed: {clip["file"]}')
        truth = CORRECTIONS.get(clip['file'], {}).get('raga', clip['raga_canonical'])
        audio, decoder = decodable(path, digest)
        duration = float(sf.info(str(audio)).duration)
        result = identify_raga(candidate, audio, digest, 0.0, min(duration, 180.), CACHE, gate)
        known = fold(truth) in class_keys
        row = dict(file=clip['file'], duration_s=duration, truth=truth, decoder=decoder,
                   frozen_label=clip['raga_canonical'], corrected=clip['file'] in CORRECTIONS,
                   in_vocabulary=known, answered=result['answered'], reason=result['reason'],
                   accepted=result['accepted'], signals=result['signals'],
                   tonic_hz=result['query']['tonic_hz'], voiced_s=result['voiced_s'],
                   top3=[r['raga'] for r in result['ranked'][:3]])
        row['correct'] = bool(row['top3']) and fold(row['top3'][0]) == fold(truth)
        row['top3_correct'] = fold(truth) in {fold(c) for c in row['top3']}
        rows.append(row)
        print(f"{clip['file'][:40]:40s} {truth:16s} -> {row['top3'][:1]} margin "
              f"{(row['signals'] or {}).get('margin', float('nan')):.3f} {'ACCEPT' if row['accepted'] else ''}", flush=True)
    known = [r for r in rows if r['in_vocabulary']]
    oov = [r for r in rows if not r['in_vocabulary']]
    k1 = sum(r['correct'] for r in known); k3 = sum(r['top3_correct'] for r in known)
    acc = [r for r in known if r['accepted']]
    summary = dict(n_frozen=len(rows), n_in_vocabulary=len(known), n_oov=len(oov),
                   top1=k1, top1_rate=k1 / len(known), top1_wilson95=wilson(k1, len(known)),
                   top3=k3, top3_rate=k3 / len(known), top3_wilson95=wilson(k3, len(known)),
                   n_answered=sum(r['answered'] for r in known),
                   accepted=len(acc), accepted_correct=sum(r['correct'] for r in acc),
                   accepted_precision=(sum(r['correct'] for r in acc) / len(acc)) if acc else None,
                   oov_accepted=sum(r['accepted'] for r in oov),
                   oov_rows=[dict(file=r['file'], truth=r['truth'], top3=r['top3'], accepted=r['accepted']) for r in oov],
                   comparator_raga_v3_fused_whole_mix=dict(top1='16/27', top3_tier_restricted='20/27'))
    report = dict(status='frozen wild clips; whole clip; short-clip regime, not the concert companion regime',
                  prereg='data/overhaul/WILD_PREREG.md', frozen_sha256=sha(CLIPS),
                  model=candidate.describe(), gate=gate.describe(), summary=summary, rows=rows,
                  elapsed_s=time.monotonic() - started)
    write_json(a.out, report)
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
