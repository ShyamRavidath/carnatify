"""Paired, cluster-bootstrapped verdict between two fitted raga candidates.

Implements data/overhaul/CANDIDATE_VERDICT_PREREG.md. Consumes only the
per-track records already on disk (kernel_benchmark.json, evaluation180.json,
manifest.json, folds.json, annotated_corpus_v2.json); refits nothing, tunes
nothing. Every input is hashed into the report.

Usage:
  venv_train/bin/python scripts/candidate_verdict.py \
      --candidate data/overhaul/context180_recovered_experiment/training \
      --candidate-key context180_recovered \
      --comparator data/overhaul/file_artist_strict_decode \
      --comparator-key strict_decode \
      --out data/overhaul/context180_recovered_experiment/verdict.json
"""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
from normalize_ragas import fold
from scripts.raga_pipeline import sha, write_json
from scripts.summarize_overhaul import paired_interval

ARM = 'legacy_kernel_ridge'
SEED, N_BOOT = 42, 5000


def load(path):
    return json.loads(Path(path).read_text())


def cv_records(run):
    kb = load(run / 'kernel_benchmark.json')
    rows = kb['arms'][ARM]['per_track']
    return {r['track']: r for r in rows}


def dev_records(run, key):
    ev = load(run / 'evaluation180.json')
    out = {}
    for r in ev['rows']:
        out[r['track']] = dict(raga=r['raga'], source=r['source'],
                               est=r['predictions'][key + '_estimated'],
                               ann=r['predictions'][key + '_annotated'])
    return out, ev['summary']


def query_clusters(corpus_path, tracks):
    corpus = {r['track']: r for r in load(corpus_path)['rows']}
    clusters = {}
    for t in tracks:
        artists = corpus[t]['artists']
        if isinstance(artists, str):
            artists = json.loads(artists.replace("'", '"'))
        clusters[t] = '|'.join(sorted(fold(a) for a in artists)) or corpus[t]['group']
    return clusters


def paired(tracks, a_ok, b_ok, cluster_of):
    delta = [int(a_ok[t]) - int(b_ok[t]) for t in tracks]
    groups = [cluster_of[t] for t in tracks]
    ci = paired_interval(delta, groups, seed=SEED, n_boot=N_BOOT)
    ci.update(candidate_correct=int(sum(a_ok[t] for t in tracks)),
              comparator_correct=int(sum(b_ok[t] for t in tracks)),
              wins=int(sum(1 for t in tracks if a_ok[t] and not b_ok[t])),
              losses=int(sum(1 for t in tracks if b_ok[t] and not a_ok[t])))
    return ci


def macro_recall(records, tracks):
    hit, tot = defaultdict(int), defaultdict(int)
    for t in tracks:
        r = records[t]
        tot[r['truth']] += 1
        hit[r['truth']] += int(r['correct'])
    per = {c: hit[c] / tot[c] for c in tot}
    return float(np.mean(list(per.values()))), per, dict(tot)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--candidate-key', required=True)
    ap.add_argument('--comparator', type=Path, required=True)
    ap.add_argument('--comparator-key', required=True)
    ap.add_argument('--corpus', type=Path, default=ROOT / 'data/overhaul/annotated_corpus_v2.json')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()

    inputs = {}
    for run, tag in ((a.candidate, 'candidate'), (a.comparator, 'comparator')):
        for name in ('kernel_benchmark.json', 'evaluation180.json', 'folds.json', 'manifest.json'):
            inputs[f'{tag}:{name}'] = sha(run / name)
        if (run / 'raga.json').exists():
            inputs[f'{tag}:model_sha256'] = load(run / 'raga.json')['model_sha256']
    inputs['corpus'] = sha(a.corpus)
    inputs['script'] = sha(Path(__file__))
    inputs['prereg'] = sha(ROOT / 'data/overhaul/CANDIDATE_VERDICT_PREREG.md')

    # Gate 1: identity.
    A, B = cv_records(a.candidate), cv_records(a.comparator)
    fa, fb = load(a.candidate / 'folds.json')['folds'], load(a.comparator / 'folds.json')['folds']
    if set(A) != set(B): raise SystemExit('Gate 1 FAIL: CV track sets differ')
    for t in A:
        if A[t]['truth'] != B[t]['truth']: raise SystemExit(f'Gate 1 FAIL: truth differs for {t}')
        if A[t]['group'] != B[t]['group']: raise SystemExit(f'Gate 1 FAIL: group differs for {t}')
    if fa != fb: raise SystemExit('Gate 1 FAIL: fold assignment differs')
    tracks = sorted(A)
    group_of = {t: A[t]['group'] for t in tracks}
    corpus_of = {r['track']: r['corpus'] for r in load(a.candidate / 'manifest.json')['rows']}
    if set(corpus_of) != set(tracks): raise SystemExit('Gate 1 FAIL: manifest tracks differ from CV tracks')

    devA, sumA = dev_records(a.candidate, a.candidate_key)
    devB, sumB = dev_records(a.comparator, a.comparator_key)
    if set(devA) != set(devB): raise SystemExit('Gate 1 FAIL: dev query sets differ')
    for t in devA:
        if devA[t]['raga'] != devB[t]['raga']: raise SystemExit(f'Gate 1 FAIL: dev label differs for {t}')
        if devA[t]['est']['in_vocabulary'] != devB[t]['est']['in_vocabulary']:
            raise SystemExit(f'Gate 1 FAIL: vocabulary membership differs for {t}')
    dev_tracks = sorted(devA)
    known = [t for t in dev_tracks if devA[t]['est']['in_vocabulary']]
    oov = [t for t in dev_tracks if not devA[t]['est']['in_vocabulary']]
    mixed = [t for t in dev_tracks if 'gamalika' in fold(devA[t]['raga'])]
    known_single = [t for t in known if t not in mixed]
    cluster_of = query_clusters(a.corpus, dev_tracks)

    # Gate 2: reproduction of the handoff's integers from raw records.
    a_cv = {t: bool(A[t]['correct']) for t in tracks}
    b_cv = {t: bool(B[t]['correct']) for t in tracks}
    a_cv3 = {t: bool(A[t]['top3']) for t in tracks}
    b_cv3 = {t: bool(B[t]['top3']) for t in tracks}
    a_est = {t: bool(devA[t]['est']['correct']) for t in dev_tracks}
    b_est = {t: bool(devB[t]['est']['correct']) for t in dev_tracks}
    a_ann = {t: bool(devA[t]['ann']['correct']) for t in dev_tracks}
    b_ann = {t: bool(devB[t]['ann']['correct']) for t in dev_tracks}
    a_est3 = {t: bool(devA[t]['est']['top3_correct']) for t in dev_tracks}
    b_est3 = {t: bool(devB[t]['est']['top3_correct']) for t in dev_tracks}
    gate2 = dict(
        cv_candidate_correct=sum(a_cv.values()), cv_comparator_correct=sum(b_cv.values()),
        cv_wins=sum(1 for t in tracks if a_cv[t] and not b_cv[t]),
        cv_losses=sum(1 for t in tracks if b_cv[t] and not a_cv[t]),
        dev_known_candidate=sum(a_est[t] for t in known), dev_known_comparator=sum(b_est[t] for t in known),
        n_tracks=len(tracks), n_groups=len(set(group_of.values())),
        n_dev=len(dev_tracks), n_known=len(known), n_oov=len(oov), n_mixed=len(mixed),
        n_query_clusters=len(set(cluster_of.values())),
        reported_summary_candidate=sumA, reported_summary_comparator=sumB)

    # Analyses.
    archive = [t for t in tracks if corpus_of[t] == 'archive']
    compmusic = [t for t in tracks if corpus_of[t] == 'compmusic']
    mrA, perA, support = macro_recall(A, tracks)
    mrB, perB, _ = macro_recall(B, tracks)
    per_class = {c: dict(support=support[c], candidate=perA[c], comparator=perB[c],
                         delta=perA[c] - perB[c]) for c in support}
    analyses = dict(
        A1_cv_top1_all=paired(tracks, a_cv, b_cv, group_of),
        A2_cv_top3_all=paired(tracks, a_cv3, b_cv3, group_of),
        A3_cv_top1_archive=paired(archive, a_cv, b_cv, group_of),
        A3_cv_top1_compmusic=paired(compmusic, a_cv, b_cv, group_of),
        A4_macro_recall=dict(candidate=mrA, comparator=mrB, delta=mrA - mrB,
                             per_class=dict(sorted(per_class.items(), key=lambda kv: kv[1]['delta']))),
        B1_dev_est_top1_known_single=paired(known_single, a_est, b_est, cluster_of),
        B1m_dev_est_top1_mixed_only=dict(
            n=len(mixed), candidate_correct=int(sum(a_est[t] for t in mixed)),
            comparator_correct=int(sum(b_est[t] for t in mixed)),
            tracks=mixed) if mixed else None,
        B2_dev_ann_top1_known_single=paired(known_single, a_ann, b_ann, cluster_of),
        B3_dev_est_top3_known_single=paired(known_single, a_est3, b_est3, cluster_of),
        C1_oov_false_accepts=dict(
            n=len(oov),
            candidate=int(sum(devA[t]['est']['accepted'] for t in oov)),
            comparator=int(sum(devB[t]['est']['accepted'] for t in oov))),
    )
    wins_dev = [t for t in known if a_est[t] and not b_est[t]]
    losses_dev = [t for t in known if b_est[t] and not a_est[t]]

    a1, b1 = analyses['A1_cv_top1_all'], analyses['B1_dev_est_top1_known_single']
    rule1 = a1['ci95'][0] > 0
    rule2 = b1['mean'] >= 0
    promote = bool(rule1 and rule2)
    arch, comp = analyses['A3_cv_top1_archive'], analyses['A3_cv_top1_compmusic']
    b2 = analyses['B2_dev_ann_top1_known_single']
    predictions = dict(
        P1_cv_interval_excludes_zero=bool(rule1),
        P2_dev_interval_includes_zero=bool(b1['ci95'][0] <= 0 <= b1['ci95'][1]),
        P3_archive_gain_exceeds_compmusic=bool(arch['mean'] > comp['mean']),
        P4_annotated_gain_smaller_than_estimated=bool(b2['mean'] < b1['mean']))
    report = dict(
        status='paired development comparison; not a fresh test, not production evidence',
        prereg='data/overhaul/CANDIDATE_VERDICT_PREREG.md', inputs=inputs,
        candidate=str(a.candidate), comparator=str(a.comparator),
        gate1='pass', gate2=gate2, analyses=analyses,
        dev_wins=wins_dev, dev_losses=losses_dev,
        decision=dict(rule1_cv_lower_bound_above_zero=bool(rule1),
                      rule2_dev_paired_mean_nonnegative=bool(rule2),
                      promote_candidate_to_reference=promote),
        predictions=predictions, seed=SEED, bootstrap=N_BOOT)
    write_json(a.out, report)
    print(json.dumps(dict(gate2={k: v for k, v in gate2.items() if not k.startswith('reported')},
                          A1=a1, A3_archive=arch, A3_compmusic=comp, A4=dict(candidate=mrA, comparator=mrB),
                          B1=b1, B2=b2, B3=analyses['B3_dev_est_top3_known_single'],
                          B1m=analyses['B1m_dev_est_top1_mixed_only'], C1=analyses['C1_oov_false_accepts'],
                          decision=report['decision'], predictions=predictions), indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
