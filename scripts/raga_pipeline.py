#!/usr/bin/env python3
"""Reproducible local candidate pipeline; never overwrites deployed models.

data-prep -> feature-extract -> evaluate -> train -> infer
Use venv_train for extraction/inference, venv for sklearn fit if needed.
The initial corpus adapter is archive Melodia: genuine audio-derived contours,
not synthetic labels. Saraga and frozen field recordings are not training input.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
from carnatify.ml.melody_features import FEATURE_VERSION, melody_features

RUN = ROOT / 'data' / 'architecture_audit'
HOP = 128 / 44100


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def prepare(args):
    """Join validated source groups with raw contours; union duplicate sources."""
    from scripts.raga_audit_protocol import DSU
    cache = ROOT / 'data/raga_coverage/matrix.npz'
    provenance = ROOT / 'data/qmax_audit/provenance.json'
    with np.load(cache, allow_pickle=True) as z:
        meta = {str(t): (str(y), str(g)) for t, y, g in zip(z['g'], z['y'], z['gc'])}
    prov = {r['stem']: r for r in json.loads(provenance.read_text())}
    rows, skipped = [], Counter()
    for path in sorted((ROOT / 'data/raga_v2_cache/archive_v3').glob('*.npz')):
        contour = ROOT / 'data/raga_v2_cache/melodia_full' / (path.stem + '.npy')
        p = prov.get(path.stem, {})
        if not contour.exists() or not p.get('archive_identifier'):
            skipped['missing_contour_or_source'] += 1
            continue
        with np.load(path, allow_pickle=True) as d:
            tid, tonic = str(d['track_id']), float(d['tonics'][0])
        if tid not in meta or not np.isfinite(tonic) or tonic <= 0:
            skipped['missing_group_or_tonic'] += 1
            continue
        label, group = meta[tid]
        rows.append(dict(track=tid, label=label, group=group,
                         source=p['archive_identifier'], contour=str(contour.relative_to(ROOT)),
                         contour_sha256=sha(contour), tonic=tonic, hop_s=HOP,
                         audio=p['audio_path'], feature_cache_sha256=sha(path)))
    # A source split must ALSO be recording-disjoint across separate uploads.
    dsu, first = DSU(), {}
    for row in rows:
        g = row['group']; dsu.find(g)
        key = row['contour_sha256']
        if key in first:
            dsu.union(g, first[key])
        first[key] = g
    members = defaultdict(list)
    for row in rows:
        members[dsu.find(row['group'])].append(row['group'])
    for row in rows:
        row['group'] = min(members[dsu.find(row['group'])])
    # Identical recordings carrying incompatible labels are not valid supervision.
    # Check the entire input before vocabulary filtering: a conflicting rare
    # label must not disappear and silently legitimize its common-label copy.
    labels_by_sha = defaultdict(set)
    for r in rows:
        labels_by_sha[r['contour_sha256']].add(r['label'])
    conflicts = {k for k, v in labels_by_sha.items() if len(v) > 1}
    skipped['conflicting_recording_labels'] = sum(r['contour_sha256'] in conflicts for r in rows)
    rows = [r for r in rows if r['contour_sha256'] not in conflicts]
    counts = Counter(r['label'] for r in rows)
    keep = sorted(k for k, n in counts.items() if n >= args.min_tracks)
    if args.max_classes:
        keep = sorted(sorted(keep, key=lambda k: (-counts[k], k))[:args.max_classes])
    rows = [r for r in rows if r['label'] in keep]
    write_json(args.run / 'manifest.json', dict(
        schema=1, corpus='archive_only', role='development', rows=rows,
        skipped=dict(skipped), inputs={str(cache.relative_to(ROOT)): sha(cache),
                                     str(provenance.relative_to(ROOT)): sha(provenance)},
        protocol=dict(window_s=60, offsets=[0.2, 0.5, 0.8], folds=5, seed=42,
                      min_tracks=args.min_tracks, max_classes=args.max_classes,
                      group='source/known_artist union identical contour',
                      status='development benchmark, not a production or field estimate')))
    print(f'Prepared {len(rows)} tracks, {len(set(r["label"] for r in rows))} classes; {dict(skipped)}')


def extract(args):
    manifest = args.run / 'manifest.json'
    rows = json.loads(manifest.read_text())['rows']
    features, legacy, labels, tracks, groups, skipped = [], [], [], [], [], []
    for row in rows:
        path = ROOT / row['contour']
        if sha(path) != row['contour_sha256']:
            raise ValueError(f'contour changed: {path}')
        f0 = np.load(path)
        width = round(60 / row['hop_s'])
        starts = sorted({round(max(0, len(f0) - width) * q) for q in (0.2, 0.5, 0.8)})
        for start in starts:
            clip = f0[start:start + width]
            if np.sum(np.isfinite(clip) & (clip > 0)) * row['hop_s'] < 10:
                skipped.append([row['track'], start, 'less_than_10s_voiced']); continue
            current = melody_features(clip, row['tonic'], row['hop_s'])
            old = melody_features(clip, row['tonic'], row['hop_s'], legacy=True)
            if current is None or old is None:
                skipped.append([row['track'], start, 'no_valid_transitions']); continue
            features.append(np.r_[current[0], current[1]])
            legacy.append(old[1]); labels.append(row['label'])
            tracks.append(row['track']); groups.append(row['group'])
    if not features:
        raise ValueError('No usable windows')
    np.savez_compressed(args.run / 'features.npz', X=np.asarray(features),
                        legacy=np.asarray(legacy), y=np.array(labels),
                        track=np.array(tracks), group=np.array(groups),
                        version=FEATURE_VERSION, manifest_sha256=sha(manifest))
    write_json(args.run / 'extraction.json', dict(windows=len(features), rejected=skipped,
                                                version=FEATURE_VERSION))
    print(f'Extracted {len(features)} windows; {len(skipped)} rejected')


def load_features(run):
    z = np.load(run / 'features.npz')
    if str(z['version']) != FEATURE_VERSION or str(z['manifest_sha256']) != sha(run / 'manifest.json'):
        raise ValueError('Stale feature cache: regenerate feature-extract')
    return z


def evaluate(args):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.metrics import balanced_accuracy_score, f1_score
    z = load_features(args.run)
    y, track, group = z['y'], z['track'], z['group']
    classes = sorted(set(y)); index = {c: i for i, c in enumerate(classes)}
    yi = np.array([index[c] for c in y])
    # Split once per track, not per augmented/window row; persist identical folds.
    tids, first = np.unique(track, return_index=True)
    splitter = StratifiedGroupKFold(5, shuffle=True, random_state=42)
    splits, fold_ids = [], np.full(len(y), -1)
    for fold, (tr, te) in enumerate(splitter.split(first, yi[first], group[first])):
        train = np.flatnonzero(np.isin(track, tids[tr]))
        test = np.flatnonzero(np.isin(track, tids[te]))
        if set(group[train]) & set(group[test]):
            raise AssertionError('source leakage')
        splits.append((train, test)); fold_ids[test] = fold
    report = dict(feature_sha256=sha(args.run / 'features.npz'), seed=42,
                  trees=args.trees, class_weight='balanced_subsample',
                  status='development CV; paired ablation, no field/SOTA claim',
                  classes=classes, n_tracks=len(tids), n_groups=len(set(group)),
                  folds={str(t): int(fold_ids[i]) for t, i in zip(tids, first)}, arms={})
    for arm, X in [('legacy_tdms', z['legacy']), ('elapsed_tdms', z['X'][:, 480:]),
                   ('elapsed_hist_tdms', z['X'])]:
        start = time.monotonic()
        pred = np.zeros((len(y), len(classes)))
        for tr, te in splits:
            model = RandomForestClassifier(n_estimators=args.trees, random_state=42,
                                            class_weight='balanced_subsample', n_jobs=4)
            counts = Counter(track[tr])
            model.fit(X[tr], yi[tr], sample_weight=np.array([1/counts[t] for t in track[tr]]))
            pred[np.ix_(te, model.classes_)] = model.predict_proba(X[te])
        p = np.stack([pred[track == t].mean(axis=0) for t in tids])
        truth = yi[first]; order = np.argsort(-p, axis=1)
        correct = order[:, 0] == truth
        per_track = [dict(track=str(t), group=str(group[i]), truth=str(y[i]),
                          prediction=classes[int(o[0])], correct=bool(ok),
                          top3=bool(yi[i] in o[:3]))
                     for t, i, o, ok in zip(tids, first, order, correct)]
        report['arms'][arm] = dict(top1=float(correct.mean()),
            top3=float(np.mean([r['top3'] for r in per_track])),
            macro_recall=float(balanced_accuracy_score(truth, order[:, 0])),
            macro_f1=float(f1_score(truth, order[:, 0], average='macro', zero_division=0)),
            majority_baseline=max(Counter(truth).values()) / len(truth),
            fit_seconds=time.monotonic()-start, per_track=per_track)
        write_json(args.run / 'benchmark.json', report)
        print(arm, {k: v for k, v in report['arms'][arm].items() if k != 'per_track'}, flush=True)
    summarize(args)


def summarize(args):
    """Paired source-cluster bootstrap; windows and tracks are not IID."""
    path = args.run / 'benchmark.json'
    report = json.loads(path.read_text())
    base = report['arms']['legacy_tdms']['per_track']
    groups = sorted({r['group'] for r in base})
    index = {g:i for i,g in enumerate(groups)}
    den = np.bincount([index[r['group']] for r in base], minlength=len(groups))
    sampled = np.random.default_rng(42).integers(0,len(groups),(2000,len(groups)))
    bootstrap = {}
    for name, arm in report['arms'].items():
        rows=arm['per_track']
        if [r['track'] for r in rows] != [r['track'] for r in base]:
            raise ValueError('unpaired benchmark')
        hits = np.bincount([index[r['group']] for r in rows],
                           weights=[r['correct'] for r in rows],minlength=len(groups))
        rates = hits[sampled].sum(1)/den[sampled].sum(1)
        arm['top1_source_cluster_ci95']=np.quantile(rates,[.025,.975]).tolist()
        bootstrap[name]=rates
    for name, arm in report['arms'].items():
        arm['delta_vs_legacy_ci95']=np.quantile(bootstrap[name]-bootstrap['legacy_tdms'],[.025,.975]).tolist()
    report['bootstrap']=dict(unit='source_group',replicates=2000,seed=42)
    write_json(path,report)


def train(args):
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    z = load_features(args.run)
    model = RandomForestClassifier(n_estimators=args.trees, random_state=42,
                                    class_weight='balanced_subsample', n_jobs=4)
    # Equal total sample mass per source track (short tracks have fewer windows).
    counts = Counter(z['track'])
    weights = np.array([1 / counts[t] for t in z['track']])
    model.fit(z['X'], z['y'], sample_weight=weights)
    bundle = dict(model=model, feature_version=FEATURE_VERSION, window_s=60,
                  feature_sha256=sha(args.run / 'features.npz'),
                  manifest_sha256=sha(args.run / 'manifest.json'),
                  status='unpromoted development candidate')
    joblib.dump(bundle, args.run / 'candidate.joblib')
    print(f'Trained candidate: {len(model.classes_)} classes')


def infer(args):
    import joblib
    import soundfile as sf
    from carnatify.audio.utils import load_audio_window
    import essentia.standard as es
    if (not np.isfinite(args.start) or args.start < 0 or
            (args.duration is not None and (not np.isfinite(args.duration) or args.duration <= 0))):
        raise ValueError('start must be finite/nonnegative and duration finite/positive')
    bundle = joblib.load(args.run / 'candidate.joblib')
    if bundle['feature_version'] != FEATURE_VERSION:
        raise ValueError('Incompatible model feature version')
    model = bundle['model']; duration = sf.info(str(args.audio)).duration
    if args.start >= duration:
        raise ValueError('start is beyond the recording')
    end = min(duration, args.start + args.duration) if args.duration else duration
    results = []
    audio_hash, model_hash = sha(args.audio), sha(args.run / 'candidate.joblib')
    for start in np.arange(args.start, end, bundle['window_s']):
        length = min(bundle['window_s'], end - start)
        row = dict(start_s=float(start), end_s=float(start+length))
        try:
            y, sr, diag = load_audio_window(args.audio, float(start), length)
            row['audio'] = diag
            if length < 10 or diag['rms'] < 1e-5:
                raise ValueError('insufficient_audio')
            tonic = float(es.TonicIndianArtMusic(sampleRate=sr)(y))
            f0, _ = es.PredominantPitchMelodia(sampleRate=sr, frameSize=2048, hopSize=128)(es.EqualLoudness(sampleRate=sr)(y))
            voiced_s = float(np.sum(f0 > 0) * HOP)
            if voiced_s < 10:
                raise ValueError('less_than_10s_voiced')
            features = melody_features(f0, tonic, HOP)
            if features is None:
                raise ValueError('no_valid_transitions')
            p = model.predict_proba(np.r_[features[0], features[1]][None])[0]
            order = np.argsort(-p)[:5]
            row.update(tonic_hz=tonic, voiced_s=voiced_s, status='candidate_uncalibrated',
                       probabilities={str(c):float(v) for c,v in zip(model.classes_,p)},
                       candidates=[dict(raga=str(model.classes_[i]), score=float(p[i])) for i in order])
        except (ValueError, RuntimeError) as exc:
            row.update(status='abstained', reason=str(exc))
        results.append(row)
        write_json(args.output, dict(audio=str(args.audio), audio_sha256=audio_hash,
            model_sha256=model_hash, feature_version=FEATURE_VERSION,
            segmentation='fixed windows; boundaries are NOT inferred item boundaries', windows=results))
        print(f'{start:.1f}s: {row["status"]}', flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, default=RUN)
    sub = ap.add_subparsers(dest='stage', required=True)
    p = sub.add_parser('data-prep'); p.add_argument('--min-tracks', type=int, default=10)
    p.add_argument('--max-classes', type=int, default=0)
    sub.add_parser('feature-extract')
    sub.add_parser('summarize')
    for name in ['evaluate', 'train']:
        p = sub.add_parser(name); p.add_argument('--trees', type=int, default=64)
    p = sub.add_parser('infer'); p.add_argument('audio', type=Path)
    p.add_argument('--start', type=float, default=0); p.add_argument('--duration', type=float)
    p.add_argument('--output', type=Path, default=RUN / 'inference.json')
    args = ap.parse_args(); args.run.mkdir(parents=True, exist_ok=True)
    {'data-prep': prepare, 'feature-extract': extract, 'evaluate': evaluate,
     'train': train, 'infer': infer, 'summarize':summarize}[args.stage](args)


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    main()
