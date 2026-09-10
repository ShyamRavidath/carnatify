"""Synthetic multi-item stress test; not independent natural-concert accuracy.

Concatenates three fixed hash-selected, different-raga 90s source excerpts
with 10s digital silence. No labels or predictions select excerpt boundaries.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import joblib
import numpy as np
import soundfile as sf
from normalize_ragas import fold
from scripts.raga_pipeline import sha, write_json
from carnatify.audio.utils import load_audio_window


def score_windows(windows, truth):
    """Score only single-item contexts as raga queries; mixed ones separately.

    The dominant label is diagnostic, never assigned as gold to mixed audio.
    Silence and missing predictions stay in the reported denominators.
    """
    rows = []
    for window in windows:
        a, b = window['start_s'], window['end_s']
        if not np.isfinite([a, b]).all() or b <= a:
            raise ValueError('Invalid query bounds')
        overlaps = [(t, max(0., min(b, t['end_s']) - max(a, t['start_s']))) for t in truth]
        musical = [(t, seconds) for t, seconds in overlaps if t['kind'] == 'music' and seconds > 0]
        coverage = sum(seconds for _, seconds in overlaps)
        if not np.isclose(coverage, b-a):
            raise ValueError('Truth must cover each query exactly once')
        dominant = max(musical, key=lambda item: item[1]) if musical else None
        purity = dominant[1] / (b-a) if dominant else 0.
        pure = len(musical) == 1 and np.isclose(purity, 1.)
        probabilities = window.get('probabilities', {})
        prediction = max(probabilities, key=probabilities.get) if probabilities else None
        rows.append(dict(start_s=a, end_s=b, pure_single_item=bool(pure),
            musical_items=len(musical), dominant_fraction=purity,
            candidate=prediction, dominant_raga=dominant[0]['raga'] if dominant else None,
            correct=(fold(prediction or '') == fold(dominant[0]['raga'])) if pure else None,
            status=window['status']))
    pure = [r for r in rows if r['pure_single_item']]
    return dict(n_windows=len(rows), n_pure=len(pure),
        n_pure_correct=sum(r['correct'] for r in pure),
        pure_accuracy=sum(r['correct'] for r in pure)/len(pure) if pure else None,
        n_mixed=sum(r['musical_items'] > 1 for r in rows), rows=rows)


def score_timeline(segments, truth):
    """Duration-weighted candidate accuracy; abstentions are not dropped."""
    musical_s = correct_s = proposed_s = asserted_s = 0.
    for item in truth:
        if item['kind'] != 'music':
            continue
        musical_s += item['end_s'] - item['start_s']
        for segment in segments:
            overlap = max(0., min(item['end_s'], segment['end_s']) -
                          max(item['start_s'], segment['start_s']))
            candidates = segment.get('candidates', [])
            if candidates:
                proposed_s += overlap
                if fold(candidates[0]['raga']) == fold(item['raga']):
                    correct_s += overlap
            if segment.get('status') == 'recognized' and segment.get('raga'):
                asserted_s += overlap
    return dict(musical_s=musical_s, candidate_correct_s=correct_s,
                candidate_accuracy=correct_s/musical_s if musical_s else None,
                candidate_coverage_s=proposed_s, asserted_identity_s=asserted_s)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--reports', nargs='*', type=Path)
    args = ap.parse_args()
    cp = ROOT / 'data/overhaul/annotated_corpus.json'
    corpus = json.loads(cp.read_text())['rows']
    bundle = joblib.load(args.model)
    vocabulary = {fold(str(c)) for c in bundle['model'].classes_}
    chosen = []; ragas = set()
    for row in sorted(corpus, key=lambda r: hashlib.sha256(r['track'].encode()).hexdigest()):
        raga = fold(row['raga'])
        if raga not in vocabulary or raga in ragas:
            continue
        if row['track'] in bundle.get('training_track_ids', []):
            raise ValueError('Evaluation track explicitly appears in training')
        path = ROOT / row['audio']; duration = sf.info(path).duration
        if duration < 90:
            continue
        chosen.append(dict(track=row['track'], audio=row['audio'], audio_sha256=sha(path),
                           raga=row['raga'], start_s=(duration-90)/2, duration_s=90.))
        ragas.add(raga)
        if len(chosen) == 3:
            break
    if len(chosen) != 3:
        raise ValueError('Insufficient eligible sources')
    truth = []; cursor = 0.
    for i, query in enumerate(chosen):
        if i:
            truth.append(dict(start_s=cursor, end_s=cursor+10, kind='silence'))
            cursor += 10
        truth.append(dict(start_s=cursor, end_s=cursor+90, kind='music', raga=query['raga'], track=query['track']))
        cursor += 90
    plan = dict(status='synthetic transition development stress test, not natural-concert validation',
        policy='three distinct in-vocabulary ragas; track-SHA order; centered 90s; 10s silence; no score-based selection',
        corpus_sha256=sha(cp), model_sha256=sha(args.model), sample_rate=44100,
        queries=chosen, truth=truth, duration_s=cursor)
    args.run.mkdir(parents=True, exist_ok=True)
    pp = args.run / 'plan.json'
    if pp.exists() and json.loads(pp.read_text()) != plan:
        raise ValueError('Changed protocol; use a new run')
    if not pp.exists():
        write_json(pp, plan)
    audio = args.run / 'concert.wav'; receipt = args.run / 'audio.json'
    if audio.exists():
        if not receipt.exists():
            raise ValueError('Unverified existing synthetic audio')
        saved = json.loads(receipt.read_text())
        if saved['plan_sha256'] != sha(pp) or saved['audio_sha256'] != sha(audio):
            raise ValueError('Synthetic audio provenance mismatch')
    else:
        temporary = args.run / 'concert.partial.wav'
        with sf.SoundFile(temporary, mode='w', samplerate=44100, channels=1, subtype='FLOAT') as output:
            for i, query in enumerate(chosen):
                if i:
                    output.write(np.zeros(441000, np.float32))
                y, sr, _ = load_audio_window(ROOT/query['audio'], query['start_s'], 90., 44100)
                if sr != 44100 or len(y) != 90*44100:
                    raise ValueError('Unexpected excerpt duration')
                output.write(y)
        temporary.replace(audio)
        write_json(receipt, dict(plan_sha256=sha(pp), audio_sha256=sha(audio)))
    for path in args.reports or []:
        report = json.loads(path.read_text())
        if report['audio_sha256'] != sha(audio) or report['model_sha256'] != sha(args.model):
            raise ValueError('Prediction inputs differ from frozen plan')
        if report['duration_s'] != cursor:
            raise ValueError('Incomplete concert prediction')
        result = dict(status=plan['status'], plan_sha256=sha(pp), report_sha256=sha(path),
                      context_s=report['raga_context_s'],
                      context_policy=report.get('silence_boundary_policy') or
                          ('event_tags_only' if report.get('silence_bounded_context') else 'fixed'),
                      timeline=score_timeline(report['segments'], truth),
                      **score_windows(report['windows'], truth))
        write_json(args.run / (path.stem + '_score.json'), result)
        print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
    print(f'Frozen synthetic concert: {audio}; {cursor:.0f}s', flush=True)


if __name__ == '__main__':
    main()
