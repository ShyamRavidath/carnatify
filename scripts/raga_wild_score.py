"""Wild raga measurement, stage 3 — score the exported models. Read-only.

Per `data/raga_wild/PREREGISTRATION.md` §3 and §6.

  * **Primary**: the exported *fused* model, exactly as a product would run it —
    `P = (1 - w)*P_tdms + w*P_hist` with `w = FUSION_W_HIST` read from
    `models/raga_v3_meta.json` (0.4). 32 classes, as exported.
  * **Secondary**: TDMS-only (`models/raga_v3_tdms_rf.pkl`), the configuration
    whose source-disjoint archive score is 72.2/84.0 — identical to
    `data/RAGA_CONTAMINATION_AUDIT.md` level (c) — so it is comparable to the
    audit series.
  * **Registered restricted read-out**: each posterior restricted to the 18
    ragas of the frozen tier and renormalised. This is the figure directly
    comparable to the domain job's 48.7% and to the 1/18 chance floor; the
    unrestricted one is what a product would emit.

  * 95% CI: **Wilson score**, unit = the clip. n = 29.
  * Paired arm comparison: **exact McNemar** (two-sided binomial on the
    discordant pairs), demucs vs mix, fused, whole clip.

Nothing under `models/` is written. Runs under either venv (both carry the
sklearn the pickles were written by).

Usage: venv/bin/python scripts/raga_wild_score.py
"""
from __future__ import annotations

import json
import math
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT_DIR = ROOT / 'data' / 'raga_wild'
ROW_DIR = OUT_DIR / 'rows'
MODELS = ROOT / 'models'

ARMS = ('mix', 'mix_voiceband', 'demucs')
WINDOWS = ('whole', 'w60')
PRIMARY_ARM = 'mix'
PRIMARY_WINDOW = 'whole'          # "best available window", fixed in prereg §2


def fold(s: str) -> str:
    d = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in d if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum())


def wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(a_only: int, b_only: int) -> float:
    """Two-sided exact binomial on the discordant pairs."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def pct(k: int, n: int) -> str:
    if n == 0:
        return 'n/a'
    lo, hi = wilson(k, n)
    return f'{k}/{n} = {100 * k / n:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]'


def load_rows() -> list[dict]:
    rows = []
    for p in sorted(ROW_DIR.glob('*.npz')):
        d = np.load(p, allow_pickle=True)
        meta = json.loads(str(d['meta']))
        meta['_feats'] = {k: d[k] for k in d.files if k != 'meta'}
        rows.append(meta)
    return rows


def load_models():
    import joblib
    meta = json.loads((MODELS / 'raga_v3_meta.json').read_text())
    rf_t = joblib.load(MODELS / 'raga_v3_tdms_rf.pkl')
    rf_h = joblib.load(MODELS / 'raga_v3_hist_rf.pkl')
    le = joblib.load(MODELS / 'raga_v3_label_encoder.pkl')
    classes = [str(c) for c in le.classes_]
    return rf_t, rf_h, classes, float(meta['fusion_w_hist']), meta


def topk(proba: np.ndarray, classes: list[str], keep: np.ndarray | None, k: int = 5):
    p = proba.copy()
    if keep is not None:
        p = p * keep
        s = p.sum()
        p = p / s if s > 0 else p
    order = np.argsort(-p)[:k]
    return [(classes[i], float(p[i])) for i in order], p


def rank_of(proba: np.ndarray, classes: list[str], truth: str,
            keep: np.ndarray | None) -> int | None:
    p = proba if keep is None else proba * keep
    tf = fold(truth)
    idx = [i for i, c in enumerate(classes) if fold(c) == tf]
    if not idx:
        return None
    if keep is not None and not keep[idx[0]]:
        return None
    return int((p > p[idx[0]]).sum() + 1)


def main() -> None:
    proto = json.loads((OUT_DIR / 'protocol.json').read_text())
    frozen = json.loads((OUT_DIR / 'FROZEN_CLIPS.json').read_text())
    tier = frozen['tier']
    rows = load_rows()
    rf_t, rf_h, classes, w_hist, mmeta = load_models()
    keep = np.array([fold(c) in {fold(t) for t in tier} for c in classes], dtype=float)
    print(f'exported model: {len(classes)} classes (min_tracks={mmeta["min_tracks"]}), '
          f'fusion w_hist={w_hist}', flush=True)
    print(f'tier ragas present in the model label set: {int(keep.sum())}/{len(tier)}',
          flush=True)
    missing = [t for t in tier if fold(t) not in {fold(c) for c in classes}]
    if missing:
        print(f'  TIER RAGAS ABSENT FROM THE EXPORTED MODEL: {missing}', flush=True)

    by_key = {r['key']: r for r in rows}
    files = [c['file'] for c in frozen['clips']]
    truth = {c['file']: c['raga_canonical'] for c in frozen['clips']}
    stem_key = {c['file']: ''.join(ch if ch.isalnum() else '_' for ch in Path(c['file']).stem)
                for c in frozen['clips']}

    # ------------------------------------------------------------- predictions
    # cell -> file -> dict(top1, top1_p, top3, rank, correct1, correct3)
    cells: dict[tuple, dict] = {}
    per_clip: list[dict] = []
    outcomes: dict[tuple, Counter] = {}

    for f in files:
        for win in WINDOWS:
            key = f'{stem_key[f]}__{win}'
            r = by_key.get(key)
            if r is None:
                continue
            feats = r['_feats']
            hrow = feats.get('hist')
            p_h = rf_h.predict_proba(hrow[None, :].astype(np.float64))[0] if hrow is not None else None
            base = dict(file=f, window=win, truth=truth[f],
                        dur_s=r['dur_s'], start_s=r['start_s'],
                        tonic=r['tonic']['used'], tonic_raw=r['tonic'].get('raw'),
                        tonic_fallback=r['tonic']['fallback'],
                        tonic_on_vocal=r['tonic'].get('on_vocal_diagnostic'),
                        hist_outcome=r['hist']['outcome'])
            for arm in ARMS:
                ao = r['arms'][arm]
                outcomes.setdefault((arm, win), Counter())[ao['outcome']] += 1
                trow = feats.get(f'tdms_{arm}')
                rec = dict(base, arm=arm, outcome=ao['outcome'],
                           n_voiced=ao.get('n_voiced'), density=ao.get('density'),
                           voiced_s=ao.get('voiced_s'))
                if trow is None:
                    per_clip.append(rec)
                    continue
                p_t = rf_t.predict_proba(trow[None, :].astype(np.float64))[0]
                for model in ('fused', 'tdms'):
                    if model == 'fused':
                        if p_h is None:
                            continue
                        proba = (1 - w_hist) * p_t + w_hist * p_h
                    else:
                        proba = p_t
                    for scope, kp in (('all', None), ('tier', keep)):
                        t5, p = topk(proba, classes, kp)
                        rk = rank_of(proba, classes, truth[f], kp)
                        c1 = fold(t5[0][0]) == fold(truth[f])
                        c3 = any(fold(c) == fold(truth[f]) for c, _ in t5[:3])
                        c5 = any(fold(c) == fold(truth[f]) for c, _ in t5[:5])
                        cells.setdefault((model, scope, arm, win), {})[f] = dict(
                            top1=t5[0][0], top1_p=t5[0][1],
                            top3=[c for c, _ in t5[:3]], top5=[c for c, _ in t5[:5]],
                            rank=rk, c1=c1, c3=c3, c5=c5)
                        rec[f'{model}_{scope}_top1'] = t5[0][0]
                        rec[f'{model}_{scope}_p'] = round(t5[0][1], 3)
                        rec[f'{model}_{scope}_rank'] = rk
                        rec[f'{model}_{scope}_c1'] = c1
                        rec[f'{model}_{scope}_c3'] = c3
                per_clip.append(rec)

    n_all = len(files)

    # ------------------------------------------------------------------ tables
    print('\n== OUTCOMES (mutually exclusive, never summed)', flush=True)
    for (arm, win), c in sorted(outcomes.items()):
        print(f'  {arm:<14} {win:<6} {dict(c)}', flush=True)
    nfb = sum(1 for r in per_clip if r['arm'] == 'mix' and r['window'] == 'whole'
              and r['tonic_fallback'])
    print(f'  tonic fallback fired on {nfb}/{n_all} clips (whole clip)', flush=True)

    def summarise(model, scope, arm, win):
        d = cells.get((model, scope, arm, win), {})
        k1 = sum(1 for v in d.values() if v['c1'])
        k3 = sum(1 for v in d.values() if v['c3'])
        k5 = sum(1 for v in d.values() if v['c5'])
        n = len(d)
        return dict(model=model, scope=scope, arm=arm, window=win, n_scored=n,
                    n_clips=n_all, top1=k1, top3=k3, top5=k5,
                    top1_pct=(100 * k1 / n) if n else None,
                    top1_ci=[100 * x for x in wilson(k1, n)] if n else None,
                    top3_pct=(100 * k3 / n) if n else None,
                    top3_ci=[100 * x for x in wilson(k3, n)] if n else None,
                    top1_pct_of29=100 * k1 / n_all, top3_pct_of29=100 * k3 / n_all,
                    top1_ci_of29=[100 * x for x in wilson(k1, n_all)],
                    top3_ci_of29=[100 * x for x in wilson(k3, n_all)])

    summary = {}
    print('\n== READ-OUTS (n scored / n frozen; Wilson 95% CI)', flush=True)
    hdr = f"  {'model':<6} {'scope':<5} {'arm':<14} {'win':<6} {'top-1':<28} {'top-3':<28}"
    print(hdr, flush=True)
    for model in ('fused', 'tdms'):
        for scope in ('all', 'tier'):
            for arm in ARMS:
                for win in WINDOWS:
                    s = summarise(model, scope, arm, win)
                    if not s['n_scored']:
                        continue
                    summary[f'{model}|{scope}|{arm}|{win}'] = s
                    star = ' <-- PRIMARY' if (model == 'fused' and scope == 'all'
                                              and arm == PRIMARY_ARM
                                              and win == PRIMARY_WINDOW) else ''
                    print(f"  {model:<6} {scope:<5} {arm:<14} {win:<6} "
                          f"{pct(s['top1'], s['n_scored']):<28} "
                          f"{pct(s['top3'], s['n_scored']):<28}{star}", flush=True)

    # --------------------------------------------------------------- McNemar
    print('\n== PAIRED (exact McNemar, fused, whole clip)', flush=True)
    mc = {}
    for scope in ('all', 'tier'):
        a = cells.get(('fused', scope, 'mix', 'whole'), {})
        b = cells.get(('fused', scope, 'demucs', 'whole'), {})
        common = sorted(set(a) & set(b))
        b_only = sum(1 for f in common if b[f]['c1'] and not a[f]['c1'])
        a_only = sum(1 for f in common if a[f]['c1'] and not b[f]['c1'])
        p = mcnemar_exact(a_only, b_only)
        mc[scope] = dict(n_common=len(common), demucs_only=b_only, mix_only=a_only, p=p)
        print(f'  {scope}: n={len(common)}  demucs-only {b_only}  mix-only {a_only}  '
              f'exact p={p:.3f}', flush=True)

    # --------------------------------- window: whole vs 60 s on the SAME clips
    print('\n== WINDOW, paired on the clips that have both (fused, mix)', flush=True)
    win_pair = {}
    for scope in ('all', 'tier'):
        a = cells.get(('fused', scope, 'mix', 'whole'), {})
        b = cells.get(('fused', scope, 'mix', 'w60'), {})
        common = sorted(set(a) & set(b))
        ka = sum(1 for f in common if a[f]['c1'])
        kb = sum(1 for f in common if b[f]['c1'])
        p = mcnemar_exact(sum(1 for f in common if a[f]['c1'] and not b[f]['c1']),
                          sum(1 for f in common if b[f]['c1'] and not a[f]['c1']))
        win_pair[scope] = dict(n=len(common), whole=ka, w60=kb, p=p)
        print(f'  {scope}: n={len(common)}  whole {pct(ka, len(common))}  '
              f'60s {pct(kb, len(common))}  exact p={p:.3f}', flush=True)

    # ------------------------------------------------------- per-raga, primary
    print('\n== PER-RAGA (fused, all-class, mix, whole clip)', flush=True)
    d = cells.get(('fused', 'all', 'mix', 'whole'), {})
    dt = cells.get(('fused', 'tier', 'mix', 'whole'), {})
    per_raga = {}
    for r in sorted({truth[f] for f in d}):
        fs = [f for f in d if truth[f] == r]
        per_raga[r] = dict(n=len(fs), top1=sum(1 for f in fs if d[f]['c1']),
                           top3=sum(1 for f in fs if d[f]['c3']),
                           top1_tier=sum(1 for f in fs if dt[f]['c1']))
        print(f"  {r:<18} n={len(fs)}  top-1 {per_raga[r]['top1']}/{len(fs)}  "
              f"top-3 {per_raga[r]['top3']}/{len(fs)}", flush=True)

    # ------------------------------------------------- prediction concentration
    pred = Counter(v['top1'] for v in d.values())
    print(f'\n== PREDICTION SPREAD (fused, all, mix, whole): '
          f'{len(pred)} distinct classes predicted over {len(d)} clips; '
          f'most frequent {pred.most_common(3)}', flush=True)
    dens = [r['density'] for r in per_clip
            if r['arm'] == 'mix' and r['window'] == 'whole' and r.get('density')]
    vs = [r['voiced_s'] for r in per_clip
          if r['arm'] == 'mix' and r['window'] == 'whole' and r.get('voiced_s')]
    print(f'   voicing density mean {np.mean(dens):.3f} '
          f'[{min(dens):.3f}, {max(dens):.3f}]; voiced seconds mean {np.mean(vs):.1f} '
          f'[{min(vs):.1f}, {max(vs):.1f}]', flush=True)

    # ------------------------------------------------------------ rank profile
    print('\n== RANK OF THE TRUE RAGA (fused, mix, whole clip)', flush=True)
    for scope in ('all', 'tier'):
        d = cells.get(('fused', scope, 'mix', 'whole'), {})
        rk = [v['rank'] for v in d.values() if v['rank']]
        if rk:
            print(f'  {scope}: median {np.median(rk):.0f}  mean {np.mean(rk):.1f}  '
                  f'top-5 {sum(1 for r in rk if r <= 5)}/{len(d)}  '
                  f'worst {max(rk)}  (of {int(keep.sum()) if scope == "tier" else len(classes)} classes)',
                  flush=True)

    # ------------------------------------------------------------- per clip
    print('\n== PER-CLIP (fused, all-class, mix arm)', flush=True)
    for f in files:
        for win in WINDOWS:
            d = cells.get(('fused', 'all', 'mix', win), {}).get(f)
            dt = cells.get(('fused', 'tier', 'mix', win), {}).get(f)
            if d is None:
                continue
            print(f"  {f:<46} {win:<6} truth={truth[f]:<16} "
                  f"top1={d['top1']:<16} p={d['top1_p']:.2f} "
                  f"rank={d['rank']}  {'HIT' if d['c1'] else ('t3' if d['c3'] else '.')}"
                  f"  tier-top1={dt['top1'] if dt else '-'}"
                  f" {'HIT' if dt and dt['c1'] else ''}", flush=True)

    # ------------------------------------------------- markdown for the write-up
    md = ['### Per-clip — fused model, `mix` arm (whole clip, and the 60 s window '
          'where the clip has one)', '',
          '| clip | dur | truth | top-1 (32-class) | p | rank | hit | top-1 '
          '(18-class) | hit | 60 s top-1 | hit |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    for f in files:
        a = cells.get(('fused', 'all', 'mix', 'whole'), {}).get(f)
        t = cells.get(('fused', 'tier', 'mix', 'whole'), {}).get(f)
        w = cells.get(('fused', 'all', 'mix', 'w60'), {}).get(f)
        dur = next((r['dur_s'] for r in per_clip
                    if r['file'] == f and r['window'] == 'whole'), 0.0)
        if a is None:
            md.append(f'| `{f}` | {dur:.1f} s | {truth[f]} | — | — | — | — | — | — '
                      f'| — | — |')
            continue
        md.append(
            f'| `{f}` | {dur:.1f} s | {truth[f]} | {a["top1"]} | {a["top1_p"]:.2f} '
            f'| {a["rank"]} | {"**Y**" if a["c1"] else ("t3" if a["c3"] else "n")} '
            f'| {t["top1"] if t else "—"} '
            f'| {"**Y**" if t and t["c1"] else ("t3" if t and t["c3"] else "n")} '
            f'| {w["top1"] if w else "—"} '
            f'| {("**Y**" if w["c1"] else ("t3" if w["c3"] else "n")) if w else "—"} |')
    md += ['', '### Read-outs', '',
           '| model | scope | arm | window | n scored | top-1 (95% CI) | '
           'top-3 (95% CI) |', '|---|---|---|---|---|---|---|']
    for k, s in summary.items():
        md.append(f"| {s['model']} | {s['scope']} | `{s['arm']}` | {s['window']} "
                  f"| {s['n_scored']}/{n_all} | {pct(s['top1'], s['n_scored'])} "
                  f"| {pct(s['top3'], s['n_scored'])} |")
    (OUT_DIR / 'tables.md').write_text('\n'.join(md))
    print(f"wrote {OUT_DIR / 'tables.md'}")

    out = dict(n_frozen=n_all, model_classes=classes, tier=tier,
               fusion_w_hist=w_hist, primary=f'fused|all|{PRIMARY_ARM}|{PRIMARY_WINDOW}',
               outcomes={f'{a}|{w}': dict(c) for (a, w), c in outcomes.items()},
               tonic_fallback_whole_mix=nfb,
               summary=summary, mcnemar=mc, window_paired=win_pair,
               per_raga=per_raga,
               cells={'|'.join(k): v for k, v in cells.items()},
               per_clip=per_clip)
    (OUT_DIR / 'results.json').write_text(json.dumps(out, ensure_ascii=False, indent=1,
                                                     default=str))
    print(f"\nwrote {OUT_DIR / 'results.json'}")


if __name__ == '__main__':
    main()
