#!/usr/bin/env python3
"""Score the duration probe under its pre-registered decision rule.

Joins `identify_clip.py --json` output against the sidecar written by
`duration_probe_cut.py`. Reads only; edits nothing in the scoreboard path.

DECLARED EXCEPTION to the frozen-scoreboard rule (HANDOFF_SESSION_0725 §7.4):
runs on different audio, graduates nothing on its own.

Rewritten 2026-07-26 after red-team review (`CODEX_DURATION_PROBE_REVIEW.md`
P0 "the gate is a noisy binary classifier, not a valid decision rule"). Four
things were wrong with the first version and are fixed here:

1. **The four observations per title are PAIRED** — same recording, same
   anchor, nested lengths — and the first version threw the pairing away into
   four marginal lists. The uncertainty of the 30→300 contrast is carried by
   the titles that FLIP, not by the marginal rates. Estimated here from the
   discordant pairs (exact McNemar/sign test) plus a cluster bootstrap.
2. **`wilson_se` was the ordinary Wald SE**, misnamed, and was the SE of a
   marginal rate rather than of the paired difference. Removed.
3. **Titles are not independent.** Several come from one archive concert and
   share artist, hall, mic and era, so the bootstrap resamples
   `archive_identifier` CLUSTERS. Titles with no known concert are their own
   cluster.
4. **The binary gate called every non-pass "P1 DEAD"** — a +14pp estimate, a
   +20pp estimate with one dip, and an interval spanning -5 to +30 all got the
   same causal verdict. The rule is now three-way, and *inconclusive* is a
   real outcome that does not move the roadmap.

Strict observed monotonicity was dropped as a condition. With four
exchangeable points only ~4% of orderings are monotone by chance, so a single
one-hit dip could veto a real effect; and a curve that jumps once then
plateaus (20/35/35/35) is monotone and would have passed anyway, while being
*favourable* product evidence rather than grounds for rejection. Shape is
reported as paired transition tables, as a diagnostic, never as a veto.

The negative arm was rebuilt on 2026-07-28 (`CODEX_NEGATIVE_ARM_REVIEW.md`).
Three things it lacked and now has:

5. **A validity gate.** It printed point rates with no bijection check, no
   cache-miss check and no stratum check, so a half-transcribed negative run
   would still have produced a confident-looking table.
6. **A frozen decision rule.** The safety claim is an exact one-sided 95%
   UPPER BOUND on the new-bluff rate, 30s -> 300s, on windows adjudicated as
   carrying no sung words. Detection at +15pp would need ~44 items that flip
   and this corpus cannot promise them; ruling a rise out is both achievable
   and what the product decision needs.
7. **A registered combination rule.** Recall is a change in top-5 hit rate
   among eligible in-catalog works; bluffing is a change in answer rate among
   negative queries. They are not subtractable and are no longer described as
   paired: the verdict is a conjunction.

Run:
  CARNATIFY_ASR_BACKEND=whisper venv_train/bin/python identify_clip.py \
      data/duration_probe/anchored --json --no-raga --cache-v2 > /tmp/probe.json
  CARNATIFY_ASR_BACKEND=whisper venv_train/bin/python identify_clip.py \
      data/duration_probe/negatives --json --no-raga --cache-v2 > /tmp/neg.json
  venv_train/bin/python scripts/duration_probe_score.py \
      --results /tmp/probe.json --truth data/duration_probe/truth_anchored.json \
      --negative-results /tmp/neg.json \
      --negative-truth data/duration_probe/truth_negatives.json
"""
import argparse
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identify_clip import audio_sha256  # noqa: E402  (one hash definition)

PROBE_ROOT = ROOT / 'data' / 'duration_probe'
NEG_AUDIO_DIR = PROBE_ROOT / 'negatives'

BOOTSTRAP = 10000
BOOT_SEED = 20260726


def exact_sign_p(gains: int, losses: int) -> float:
    """One-sided exact McNemar: P(>= `gains` successes | discordant, p=0.5)."""
    n = gains + losses
    if n == 0:
        return 1.0
    return sum(math.comb(n, i) for i in range(gains, n + 1)) / 2 ** n


def clopper_pearson_upper(b: int, n: int, alpha: float = 0.05) -> float:
    """One-sided exact upper bound on a binomial rate, by bisection on the CDF.

    The negative arm's rule is an UPPER BOUND claim, not a detection claim.
    Review measured that detecting a true +15pp bluff rise needs ~44 items that
    can flip, which this corpus cannot promise; but a modest number of clean
    items can still rule such a rise out, and ruling it out is what the product
    decision actually needs. Thresholds this reproduces, from
    `CODEX_NEGATIVE_ARM_REVIEW.md` §1: below 15pp at n>=19 with 0 new bluffs,
    n>=30 with 1, n>=40 with 2.
    """
    if n == 0:
        return 1.0
    if b >= n:
        return 1.0

    def cdf(p):
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
                   for i in range(b + 1))

    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if cdf(mid) > alpha:
            lo = mid
        else:
            hi = mid
    return hi


def power_table(n: int, boundary_pp: float = 15.0):
    """[(new bluffs, upper bound pp, does it still rule out the boundary)]."""
    return [(b, 100 * clopper_pearson_upper(b, n),
             100 * clopper_pearson_upper(b, n) < boundary_pp)
            for b in range(0, 4)]


def cluster_bootstrap(titles, short, long_, clusters, reps=BOOTSTRAP):
    """Percentile CI for the paired top-5 difference, resampling clusters."""
    by_cluster = defaultdict(list)
    for t in titles:
        by_cluster[clusters[t]].append(t)
    keys = list(by_cluster)
    rng = random.Random(BOOT_SEED)
    deltas = []
    for _ in range(reps):
        picked = [t for _ in keys
                  for t in by_cluster[keys[rng.randrange(len(keys))]]]
        if not picked:
            continue
        d = (sum(long_[t] for t in picked) - sum(short[t] for t in picked))
        deltas.append(100.0 * d / len(picked))
    deltas.sort()
    lo = deltas[int(0.05 * len(deltas))]
    hi = deltas[int(0.95 * len(deltas)) - 1]
    return lo, hi


def validate(results, windows, side, audio_dir: Path | None = None,
             verify_audio: bool = True) -> list[str]:
    """Refuse to interpret an incomplete or mutated experiment.

    `HANDOFF_VERFIER.md:79` is unambiguous that a SCORE with cache misses is
    invalid. A missing result silently shrinks a denominator and a duplicate
    silently inflates one, so both abort rather than degrade.

    The recall arm gets the same artifact binding as the negative arm
    (pre-registration §6b hole 7, extended to §5 on 2026-07-29): every window
    carries `audio_sha256` and the wavs are re-hashed here, so a window re-cut
    from a different anchor cannot pass as the one that was scored.
    """
    errs = []
    seen = defaultdict(int)
    for res in results:
        seen[Path(res.get('file', '')).stem] += 1
    dupes = [k for k, v in seen.items() if v > 1]
    if dupes:
        errs.append(f'{len(dupes)} duplicate result rows (e.g. {dupes[:3]})')
    missing = [k for k in windows if k not in seen]
    if missing:
        errs.append(f'{len(missing)} sidecar windows have no result '
                    f'(e.g. {missing[:3]})')
    extra = [k for k in seen if k not in windows]
    if extra:
        errs.append(f'{len(extra)} result rows absent from the sidecar '
                    f'(e.g. {extra[:3]})')
    misses = [Path(r.get('file', '')).stem for r in results
              if r.get('cache_v2') == 'MISS']
    if misses:
        errs.append(f'{len(misses)} ASR cache MISSes — a SCORE with misses is '
                    f'invalid (e.g. {misses[:3]})')

    per_dur = defaultdict(set)
    for stem, meta in windows.items():
        per_dur[meta['window_seconds']].add(meta['key'])
    registered = set(side.get('durations', []))
    if registered and set(per_dur) != registered:
        errs.append(f'durations {sorted(per_dur)} != registered '
                    f'{sorted(registered)}')
    if len({frozenset(v) for v in per_dur.values()}) > 1:
        errs.append('title sets differ between durations — pairing is broken')
    expected = side.get('expected_windows')
    if expected and len(windows) != expected:
        errs.append(f'sidecar holds {len(windows)} windows, expected '
                    f'{expected}')
    # `n_titles` is the registered unit count and is printed in the header, but
    # nothing checked it against the windows the sidecar actually carries. It is
    # also the field `--exclude-title` must be reconciled against (§5b), so a
    # reduced run has to re-satisfy this rather than skip it.
    n_titles = side.get('n_titles')
    keys = {m['key'] for m in windows.values()}
    if n_titles is not None and n_titles != len(keys):
        errs.append(f'sidecar n_titles {n_titles} != {len(keys)} distinct '
                    f'titles in windows')
    if verify_audio:
        errs += _verify_audio(
            windows, audio_dir or PROBE_ROOT / side.get('arm', 'anchored'),
            'recall', 'scripts/stamp_negative_shas.py --arm anchored')
    return errs


def hit_maps(rows):
    """stem-keyed rows -> per-title top1/top5/answered/correct maps."""
    t1, t5, ans, ans_ok = {}, {}, {}, {}
    for res, meta in rows:
        key = meta['key']
        truth = set(meta['truth_ids'])
        hits = [c.get('id') in truth for c in res.get('compositions', [])]
        t1[key] = int(bool(hits and hits[0]))
        t5[key] = int(any(hits))
        answered = res.get('composition_confidence') != 'none'
        ans[key] = int(answered)
        ans_ok[key] = int(answered and bool(hits and hits[0]))
    return t1, t5, ans, ans_ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True)
    ap.add_argument('--truth', required=True)
    ap.add_argument('--boundary-pp', type=float, default=15.0,
                    help='the pre-registered practically-useful effect size')
    ap.add_argument('--negative-results',
                    help='identify_clip --json over the negative windows')
    ap.add_argument('--negative-truth',
                    help='data/duration_probe/truth_negatives.json, AFTER '
                         'scripts/parse_negative_labels.py has stamped strata '
                         'into it')
    ap.add_argument('--force', action='store_true',
                    help='print metrics despite validation errors. The '
                         'decision is suppressed regardless.')
    ap.add_argument('--exclude-title', action='append', default=[],
                    metavar='TITLE_KEY',
                    help='drop one recall title from every readout '
                         '(pre-registration §5b straddler exclusion). '
                         'Repeatable.')
    ap.add_argument('--exclude-item', action='append', default=[],
                    metavar='ITEM',
                    help='drop one negative item from every readout, including '
                         'the rule A per-source counts. Repeatable.')
    ap.add_argument('--exclude-reason',
                    help='why the excluded units came out. Required whenever '
                         'anything is excluded, and printed above the verdict.')
    args = ap.parse_args()
    if (args.exclude_title or args.exclude_item) and not args.exclude_reason:
        ap.error('--exclude-reason is required whenever units are excluded: '
                 'the reason is printed above the verdict and copied into '
                 'AGENT_LOG.md')

    results = json.loads(Path(args.results).read_text())
    side = json.loads(Path(args.truth).read_text())
    windows = side['windows']

    errs = validate(results, windows, side)

    # §5b exclusions on the recall arm. The full run is validated first (above),
    # so an exclusion cannot mask an incomplete experiment; the reduced sidecar
    # is then re-validated against bookkeeping recomputed by subtraction.
    excluded_titles, tok_errs = resolve_recall_units(args.exclude_title,
                                                     windows)
    errs += tok_errs
    registered_n_titles = side.get('n_titles')
    if excluded_titles and not tok_errs:
        results, side, x_errs = apply_exclusions(results, side,
                                                 excluded_titles, 'key',
                                                 'recall title')
        errs += x_errs
        if not x_errs:
            errs += validate(results, side['windows'], side,
                             verify_audio=False)
        windows = side['windows']

    if errs:
        print('===== EXPERIMENT INVALID =====')
        for e in errs:
            print(f'  ! {e}')
        if not args.force:
            print('\nFix the run; do not interpret these numbers. '
                  '(--force prints metrics, still without a decision.)')
            sys.exit(1)

    by_dur = defaultdict(list)
    for res in results:
        meta = windows.get(Path(res.get('file', '')).stem)
        if meta:
            by_dur[meta['window_seconds']].append((res, meta))

    meta_by_key = {m['key']: m for m in windows.values()}
    clusters = {k: (m.get('archive_identifier') or f'solo:{k}')
                for k, m in meta_by_key.items()}

    durs = sorted(by_dur)
    maps = {d: hit_maps(by_dur[d]) for d in durs}

    print(f"\n===== DURATION PROBE — arm={side['arm']} seed={side['seed']} "
          f"n={side['n_titles']} titles =====")
    print('Declared exception: graduates nothing. Lyrics matcher only.\n')
    if excluded_titles:
        exclusion_block('recall arm, pre-registration §5b', excluded_titles,
                        args.exclude_reason, registered_n_titles,
                        side['n_titles'])
        if set(args.exclude_title) != excluded_titles:
            print(f'  (resolved from {sorted(set(args.exclude_title))})')
        print()
    print(f"{'window':>8} {'n':>4} {'top-1':>10} {'top-5':>10} {'top5 %':>8} "
          f"{'answered':>9} {'precision':>10} {'coverage':>9}")
    for d in durs:
        t1, t5, ans, ans_ok = maps[d]
        n = len(t5)
        a = sum(ans.values())
        prec = 100.0 * sum(ans_ok.values()) / a if a else 0.0
        print(f'{d:>7}s {n:>4} {sum(t1.values()):>7}/{n:<3} '
              f'{sum(t5.values()):>7}/{n:<3} '
              f'{100.0 * sum(t5.values()) / n:>7.1f}% {a:>9} '
              f'{prec:>9.0f}% {100.0 * a / n:>8.0f}%')

    short, long_ = durs[0], durs[-1]
    titles = sorted(set(maps[short][1]) & set(maps[long_][1]))
    s5, l5 = maps[short][1], maps[long_][1]
    gains = sum(1 for t in titles if l5[t] > s5[t])
    losses = sum(1 for t in titles if l5[t] < s5[t])
    delta = 100.0 * (gains - losses) / len(titles)
    lo, hi = cluster_bootstrap(titles, s5, l5, clusters)
    p = exact_sign_p(gains, losses)

    print(f'\n--- PAIRED CONTRAST {short}s -> {long_}s (top-5) ---')
    print(f'  wrong->right {gains}   right->wrong {losses}   '
          f'concordant {len(titles) - gains - losses}')
    print(f'  delta {delta:+.1f}pp   90% cluster-bootstrap CI '
          f'[{lo:+.1f}, {hi:+.1f}]   exact one-sided p={p:.4f}')
    n_clusters = len({clusters[t] for t in titles})
    print(f'  resampling {n_clusters} archive clusters over {len(titles)} '
          f'titles')

    print(f'\n--- SHAPE (paired transitions between adjacent windows) ---')
    for a, b in zip(durs, durs[1:]):
        ma, mb = maps[a][1], maps[b][1]
        g = sum(1 for t in titles if mb[t] > ma[t])
        l = sum(1 for t in titles if mb[t] < ma[t])
        print(f'  {a:>4}s -> {b:>4}s   +{g:<3} -{l:<3} '
              f'net {100.0 * (g - l) / len(titles):+.1f}pp')

    if 90 in maps and long_ != 90:
        m90, ml = maps[90][1], maps[long_][1]
        g = sum(1 for t in titles if ml[t] > m90[t])
        l = sum(1 for t in titles if ml[t] < m90[t])
        print(f'\n--- PRODUCT GAP 90s -> {long_}s ---')
        print(f'  net {100.0 * (g - l) / len(titles):+.1f}pp  (+{g} -{l}). '
              f'This is what Approach B has to close; P1 passing does NOT '
              f'mean it is already closed.')

    strat = defaultdict(list)
    for t in titles:
        strat[meta_by_key[t].get('n_lyric_lines', 0)].append(t)
    counts = sorted(strat)
    if len(counts) > 2:
        cut = counts[len(counts) // 2]
        lohi = {'few lyric lines (<= %d)' % cut:
                [t for t in titles
                 if meta_by_key[t].get('n_lyric_lines', 0) <= cut],
                'many lyric lines (> %d)' % cut:
                [t for t in titles
                 if meta_by_key[t].get('n_lyric_lines', 0) > cut]}
        print(f'\n--- STRATIFIED BY LYRIC LENGTH ---')
        print('  (pool selection interacts with this: works with more '
              'matchable lines give a long window more chances to win)')
        for name, ts in lohi.items():
            if not ts:
                continue
            d_ = 100.0 * sum(l5[t] - s5[t] for t in ts) / len(ts)
            print(f'  {name:<28} n={len(ts):<4} delta {d_:+.1f}pp')

    if args.negative_results and args.negative_truth:
        safe, why = report_negatives(args, args.boundary_pp)
    else:
        safe, why = False, 'negative arm not supplied'
        print('\n--- NEGATIVE ARM: NOT SUPPLIED ---')
        print('  METRIC_CONTRACT #3 (bluff rate) is unmeasured. Longer '
              'windows plausibly raise true hits and false answers together, '
              'so the decision below is about RECALL ONLY and cannot '
              'authorize showing results to a user.')

    print(f'\n--- PRE-REGISTERED THREE-WAY DECISION '
          f'(boundary {args.boundary_pp:+.0f}pp) ---')
    if excluded_titles or args.exclude_item:
        print(f'  scored at REDUCED n — recall {len(titles)} titles'
              + (f', negative arm minus {len(set(args.exclude_item))} item(s)'
                 if args.exclude_item else '')
              + f'. Reason: {args.exclude_reason}')
    if errs:
        recall = 'SUPPRESSED'
        print('  SUPPRESSED — the run did not validate.')
    elif lo >= args.boundary_pp:
        recall = 'PROMOTE'
        print(f'  RECALL PROMOTE: lower bound {lo:+.1f}pp clears the '
              f'boundary. Listening length is a practically useful lever.')
    elif hi < args.boundary_pp:
        recall = 'KILL'
        print(f'  RECALL KILL the >=15pp claim: upper bound {hi:+.1f}pp is '
              f'below the boundary. Duration is not the constraint at a '
              f'useful size.')
        print('  This does NOT by itself diagnose the cause; it rules out a '
              'useful duration effect for the lyrics matcher on this pool.')
    else:
        recall = 'INCONCLUSIVE'
        print(f'  RECALL INCONCLUSIVE: CI [{lo:+.1f}, {hi:+.1f}] spans the '
              f'boundary. Do not pivot the roadmap on this. Either accept the '
              f'indifference band or raise n.')

    # ---- how the two arms combine, registered before the run ----------------
    # They are NOT subtractable and must not be described as paired. Recall is
    # a change in top-5 hit rate among eligible in-catalog works; bluffing is a
    # change in answer rate among negative queries. Differencing them assumes
    # equal prevalence of positive and negative queries, equal cost, and that a
    # top-5 retrieval is worth as much as an answer shown to a user. None of
    # those is registered, and pretending otherwise was the review's §1
    # objection. The combination is therefore a CONJUNCTION, not an arithmetic
    # net: the roadmap moves only if the recall gain is real AND the safety
    # bound holds.
    print('\n--- COMBINED VERDICT (conjunction; the arms are NOT '
          'subtracted) ---')
    print(f'  recall: {recall}     safety: '
          f'{"SAFE" if safe else "NOT ESTABLISHED"} ({why})')
    if recall == 'PROMOTE' and safe:
        print('  PROMOTE. Longer listening buys in-catalog recall without a '
              'ruled-in *no-sahitya* bluff rise.')
        print('  SCOPE: only the no-sahitya stratum gates. OOC abstention at '
              'length is UNMEASURED')
        print('  — the OOC stratum is empty by construction and is '
              'unmeasurable from assets on')
        print('  disk (HANDOFF_SESSION_0729 §4), while METRIC_CONTRACT.md '
              'requires OOC bluffs')
        print('  separately. This verdict licenses duration as a RESEARCH '
              'lever on the archive')
        print('  domain. It does NOT authorize showing results to a user.')
    elif recall == 'PROMOTE':
        print('  HOLD. The recall gain is real, but this run cannot rule out '
              'that abstention degraded with it, so it does not authorize '
              'showing results to a user.')
    elif recall == 'KILL':
        print('  KILL stands on the recall arm alone; the safety arm cannot '
              'rescue a lever that is not there.')
    else:
        print('  Roadmap does not move.')

    print('\nQuote this block verbatim into AGENT_LOG.md. Never recompute a '
          'number by hand.')


GATING_STRATUM = 'no-sahitya'
# Independent sweeps of the scored window that must agree before an item may
# gate. Mirrors `parse_negative_labels.SWEEPS_REQUIRED`; the sidecar carries the
# value it was actually built under and this is only the fallback for sidecars
# written before the two-sweep rule existed.
SWEEPS_REQUIRED = 2

# Frozen design. A sidecar registering only 300s used to validate cleanly, at
# which point short == long, b == 0, and n=51 printed SAFE at a 5.7pp bound off
# an experiment with no contrast in it at all.
DESIGN_DURATIONS = (30, 300)
# Vocabularies. The old checks tested for one bad value and treated everything
# else — including absent — as good. `res.get('composition_confidence') !=
# 'none'` reads a MISSING field as an answer, so a run that produced nothing
# scored b=0 and could print SAFE.
CACHE_STATES = {'hit', 'MISS'}
CONFIDENCE_STATES = {'none', 'low', 'medium', 'high'}
# Reported, never gating. `sung_unidentified` is audio where somebody is
# clearly singing and no registry row can be pinned to it — a real product
# input, but not proof the work is absent from the catalog. `ooc` is populated
# only from a reviewed identity file and is empty on the current corpus.
SENSITIVITY_STRATA = ('sung_unidentified', 'ooc')

# A source is large enough to carry its own bound only if zero new bluffs in it
# would clear the boundary; below that its "safety" is uninformative rather
# than reassuring. b=0 first clears 15pp at n=19 (14.6pp), so 20 is the round
# number just past the cliff. Registered in
# `DURATION_PROBE_PREREGISTRATION.md` §6b ("every source with n >= 20"), frozen
# by Deepti on 2026-07-29; it is not a tunable.
SOURCE_MIN_N = 20


def validate_negatives(results, side, audio_dir: Path | None = None,
                       verify_audio: bool = True) -> list[str]:
    """Refuse to read a safety conclusion off an incomplete negative arm.

    §7.7 of the handoff: the previous scorer printed point rates with no gate
    at all, so a half-transcribed or mislabeled negative run would have
    produced a confident-looking table. Invalid negative data must suppress the
    safety conclusion, exactly as invalid recall data suppresses the recall
    verdict.
    """
    errs = []
    windows = side.get('windows', {})
    if not side.get('labels_applied'):
        errs.append('sidecar labels_applied is false — run '
                    'scripts/parse_negative_labels.py after the sheet comes '
                    'back')
    # Sheet 1 is a 50% duty-cycle sweep, so on its own it cannot establish "no
    # sung words anywhere in this window" (CODEX_NEGATIVE_ARM_REVIEW_R2.md
    # P0-1). A single-sweep arm must not be able to print a safety conclusion.
    required = side.get('sweeps_required', SWEEPS_REQUIRED)
    applied = side.get('sweeps_applied')
    if applied is None or applied < required:
        errs.append(f'negative labels rest on {applied} of {required} required '
                    f'sweeps — the gating windows are only half heard; run '
                    f'scripts/build_negative_complement.py and re-run '
                    f'scripts/parse_negative_labels.py')
    seen = Counter(Path(r.get('file', '')).stem for r in results)
    dupes = [k for k, v in seen.items() if v > 1]
    if dupes:
        errs.append(f'{len(dupes)} duplicate negative result rows '
                    f'(e.g. {dupes[:3]})')
    missing = [k for k in windows if k not in seen]
    if missing:
        errs.append(f'{len(missing)} negative windows have no result '
                    f'(e.g. {missing[:3]})')
    extra = [k for k in seen if k not in windows]
    if extra:
        errs.append(f'{len(extra)} negative result rows absent from the '
                    f'sidecar (e.g. {extra[:3]})')
    # Vocabulary checks, not one-bad-value checks. `cache_v2 == 'MISS'` alone
    # let a missing or malformed field through, and a run with no cache field
    # at all validated.
    bad_cache = [Path(r.get('file', '')).stem for r in results
                 if r.get('cache_v2') not in CACHE_STATES]
    if bad_cache:
        errs.append(f'{len(bad_cache)} negative rows have no usable cache_v2 '
                    f'field (e.g. {bad_cache[:3]})')
    misses = [Path(r.get('file', '')).stem for r in results
              if r.get('cache_v2') == 'MISS']
    if misses:
        errs.append(f'{len(misses)} negative ASR cache MISSes '
                    f'(e.g. {misses[:3]})')
    # `res.get('composition_confidence') != 'none'` counts a MISSING field as
    # an answer. Missing at both endpoints yields b=0 — SAFE off a run that
    # produced nothing.
    bad_conf = [Path(r.get('file', '')).stem for r in results
                if r.get('composition_confidence') not in CONFIDENCE_STATES]
    if bad_conf:
        errs.append(f'{len(bad_conf)} negative rows have no usable '
                    f'composition_confidence field (e.g. {bad_conf[:3]})')

    expected = side.get('expected_windows')
    if expected and len(windows) != expected:
        errs.append(f'negative sidecar holds {len(windows)} windows, expected '
                    f'{expected}')
    registered = set(side.get('durations', []))
    if registered != set(DESIGN_DURATIONS):
        errs.append(f'sidecar registers durations {sorted(registered)}, frozen '
                    f'design is {sorted(DESIGN_DURATIONS)}')
    per_dur = defaultdict(set)
    per_item_dur = Counter()
    strata_by_item = defaultdict(set)
    unlabeled = 0
    for stem, meta in windows.items():
        per_dur[meta['window_seconds']].add(meta['item'])
        per_item_dur[(meta['item'], meta['window_seconds'])] += 1
        if 'stratum' not in meta:
            unlabeled += 1
        else:
            strata_by_item[meta['item']].add(meta['stratum'])
    if unlabeled:
        errs.append(f'{unlabeled} negative windows carry no stratum')
    # One row per (item, duration). The stem-level duplicate check above sees
    # duplicate RESULTS; duplicated sidecar metadata slipped past it.
    dup_meta = [k for k, v in per_item_dur.items() if v > 1]
    if dup_meta:
        errs.append(f'{len(dup_meta)} (item, duration) pairs appear more than '
                    f'once in the sidecar (e.g. {dup_meta[:3]})')
    # An item labeled no-sahitya at 300s and something else at 30s is not a
    # paired observation of one window.
    split = sorted(i for i, s in strata_by_item.items() if len(s) > 1)
    if split:
        errs.append(f'{len(split)} items carry different strata at their two '
                    f'endpoints (e.g. {split[:3]})')
    if registered and set(per_dur) != registered:
        errs.append(f'negative durations {sorted(per_dur)} != registered '
                    f'{sorted(registered)}')
    if len({frozenset(v) for v in per_dur.values()}) > 1:
        errs.append('negative item sets differ between durations — the paired '
                    'transition count is not defined')

    # Self-consistency of the sidecar's own bookkeeping against the windows it
    # actually holds. None of these were checked; all are cheap.
    items = {m['item'] for m in windows.values()}
    n_items = side.get('n_items')
    if n_items is not None and n_items != len(items):
        errs.append(f'sidecar n_items {n_items} != {len(items)} distinct items '
                    f'in windows')
    if side.get('seed') is None:
        errs.append('sidecar records no seed — the draw is not reproducible')
    declared = side.get('stratum_counts')
    if declared is not None:
        actual = Counter(m['stratum'] for m in windows.values()
                         if m['window_seconds'] == max(registered or [0])
                         and 'stratum' in m)
        if dict(actual) != declared:
            errs.append(f'sidecar stratum_counts {declared} != per-item strata '
                        f'{dict(actual)}')
    # Pseudo-replication guard: the cluster cap exists so seven tracks off one
    # upload cannot pose as seven independent works. Nothing verified it held.
    gating_items = {m['item'] for m in windows.values()
                    if m.get('stratum') == GATING_STRATUM}
    clusters = [m.get('cluster') for m in windows.values()
                if m['item'] in gating_items
                and m['window_seconds'] == max(registered or [0])]
    if len(clusters) != len(set(clusters)):
        dupes_c = [c for c, v in Counter(clusters).items() if v > 1]
        errs.append(f'gating stratum reuses {len(dupes_c)} archive cluster(s) '
                    f'(e.g. {dupes_c[:3]}) — items are not independent')

    errs += _verify_gating_sources(results, windows, side, seen)
    if verify_audio:
        errs += _verify_audio(windows, audio_dir or NEG_AUDIO_DIR, 'negative',
                              'scripts/stamp_negative_shas.py')
    return errs


# ---------------------------------------------------------------- exclusions
# `DURATION_PROBE_PREREGISTRATION.md` §5b: if the device calibration says the
# hardware matters, every straddler comes out of both arms and the run is scored
# at reduced n. Straddler identity comes from the device map, never from a
# unit's score, and the excluded set is printed in the run's own output.

def apply_exclusions(results, side, excluded: set[str], unit_field: str,
                     label: str) -> tuple[list, dict, list[str]]:
    """Drop whole units from a run that has ALREADY validated in full.

    Returns `(results, side, errors)` with a reconciled copy of the sidecar.

    Exclusion is a reduction of a validated experiment, never a way to make an
    invalid one validate. The caller validates the complete run first — so a
    genuinely missing window is still fatal, and excluding a unit that was
    absent anyway cannot hide it — and then re-validates the reduced sidecar
    against its recomputed bookkeeping. `n_titles` / `n_items` /
    `expected_windows` / `stratum_counts` / `gating_source_counts` are
    *recomputed by subtraction* and re-checked, not bypassed.
    """
    windows = side['windows']
    present = {m[unit_field] for m in windows.values()}
    unknown = sorted(excluded - present)
    if unknown:
        return results, side, [
            f'{len(unknown)} excluded {label}(s) are not in the sidecar at all '
            f'({unknown[:3]}) — an exclusion list must name units the run '
            f'actually contains']

    long_ = max(side.get('durations') or DESIGN_DURATIONS)
    dropped_meta = [m for m in windows.values()
                    if m[unit_field] in excluded and m['window_seconds'] == long_]
    kept = {s: m for s, m in windows.items() if m[unit_field] not in excluded}
    kept_stems = set(kept)
    new_results = [r for r in results
                   if Path(r.get('file', '')).stem in kept_stems]

    new_side = dict(side)
    new_side['windows'] = kept
    n_removed = len(excluded)
    for field in ('n_titles', 'n_items'):
        if side.get(field) is not None:
            new_side[field] = side[field] - n_removed
    if side.get('expected_windows') is not None:
        new_side['expected_windows'] = (side['expected_windows']
                                        - (len(windows) - len(kept)))
    for field, key in (('stratum_counts', 'stratum'),
                       ('gating_source_counts', 'candidate_kind')):
        declared = side.get(field)
        if declared is None:
            continue
        out = dict(declared)
        for m in dropped_meta:
            v = m.get(key)
            # gating_source_counts covers the gating stratum only; a dropped
            # unit from another stratum does not touch it.
            if field == 'gating_source_counts' and m.get('stratum') != GATING_STRATUM:
                continue
            if v in out:
                out[v] -= 1
        new_side[field] = {k: v for k, v in out.items() if v}
    return new_results, new_side, []


def resolve_recall_units(tokens, windows) -> tuple[set[str], list[str]]:
    """Accept either a title `key` or a `probeNNNN` window-id prefix.

    `data/duration_probe/DEVICE_MAP.md` names straddlers by window id
    (`probe0051`), while the sidecar and every readout are keyed by title key
    (`evarani`). Making the operator translate between the two by hand is how a
    §5b exclusion ends up naming the wrong title, so both are accepted and an
    ambiguous or unmatched token is an error rather than a silent miss.
    """
    keys = {m['key'] for m in windows.values()}
    by_prefix = defaultdict(set)
    for stem, m in windows.items():
        by_prefix[stem.split('d')[0]].add(m['key'])
    out, errs = set(), []
    for tok in tokens:
        if tok in keys:
            out.add(tok)
        elif tok in by_prefix:
            hit = by_prefix[tok]
            if len(hit) != 1:
                errs.append(f'window id {tok!r} spans {len(hit)} title keys '
                            f'{sorted(hit)} — name the title key explicitly')
                continue
            out |= hit
        else:
            errs.append(f'{tok!r} is neither a title key nor a probeNNNN '
                        f'window id in this sidecar')
    return out, errs


def exclusion_block(label: str, excluded: set[str], reason: str,
                    registered_n, realized_n) -> None:
    """Print what came out, why, and what n is left — above any verdict."""
    print(f'\n--- EXCLUSIONS ({label}) ---')
    if not excluded:
        print('  none. Scored at the registered n.')
        return
    print(f'  excluded ({len(excluded)}): ' + ', '.join(sorted(excluded)))
    print(f'  reason: {reason}')
    print(f'  realized n: {realized_n} of {registered_n} registered')
    print('  Exclusion is mechanical (pre-registration §5b): the set comes '
          'from the device')
    print('  map, never from a unit\'s score, and it was fixed before any '
          'statistic was read.')


def _verify_gating_sources(results, windows, side, seen) -> list[str]:
    """Every registered gating source must actually be in front of the gate.

    Rule A (§6b) is a conjunction over the sources with n >= SOURCE_MIN_N, and
    `report_by_source` builds that list from whatever rows come back. A source
    that vanishes — dropped from the sidecar, or present in the sidecar with no
    result rows — therefore drops out of the conjunction *silently*, and the
    remaining sources grant a SAFE the design never authorised. Losing a source
    must suppress, exactly as losing a window does.
    """
    errs = []
    long_ = max(side.get('durations') or DESIGN_DURATIONS)
    actual = Counter(m.get('candidate_kind') for m in windows.values()
                     if m.get('stratum') == GATING_STRATUM
                     and m['window_seconds'] == long_)
    declared = side.get('gating_source_counts')
    if declared is not None and dict(actual) != declared:
        errs.append(f'sidecar gating_source_counts {declared} != gating '
                    f'stratum actually present {dict(actual)}')
    # Sidecar-side loss: a source registered at gating size that the sidecar no
    # longer carries at all.
    for kind, n in sorted((declared or {}).items()):
        if n >= SOURCE_MIN_N and not actual.get(kind):
            errs.append(f'registered gating source {kind!r} (n={n}) is absent '
                        f'from the sidecar — rule A would pass on the '
                        f'remaining sources without it')
    # Results-side loss: the sidecar still carries the source, but the run does
    # not observe it at both endpoints, so it contributes nothing to the gate.
    for kind, n in sorted(actual.items()):
        if n < SOURCE_MIN_N:
            continue
        items = {m['item'] for m in windows.values()
                 if m.get('stratum') == GATING_STRATUM
                 and m.get('candidate_kind') == kind}
        paired = {i for i in items
                  if all(any(w['item'] == i and w['window_seconds'] == d
                             and stem in seen
                             for stem, w in windows.items())
                         for d in set(side.get('durations')
                                      or DESIGN_DURATIONS))}
        if len(paired) < n:
            errs.append(f'gating source {kind!r} registers n={n} but only '
                        f'{len(paired)} of its items are paired in the results '
                        f'— rule A must not pass on a shrunken source')
    return errs


def _verify_audio(windows: dict, audio_dir: Path, what: str,
                  fix: str) -> list[str]:
    """Re-hash the window wavs and compare against the stamped SHAs.

    Filenames are not identity. Without this, correct filenames holding swapped
    or regenerated audio validate, and the ear's labels silently describe audio
    the pipeline never heard — the defect that killed the first negative arm.
    `--cache-v2` is keyed by the same hash, so labels and transcripts bind to
    one artifact rather than to a convention. Both arms are checked: on the
    recall arm there are no labels to bind, but a re-cut window carrying its
    old cached transcript is the same failure wearing different clothes.
    """
    stamped = {s: m['audio_sha256'] for s, m in windows.items()
               if m.get('audio_sha256')}
    if not stamped:
        return [f'no {what} window carries audio_sha256 — run {fix} to bind '
                f'the scored audio to the sidecar']
    if len(stamped) != len(windows):
        return [f'{len(windows) - len(stamped)} {what} windows carry no '
                f'audio_sha256']

    absent, mismatched = [], []
    for stem, sha in sorted(stamped.items()):
        wav = audio_dir / f'{stem}.wav'
        if not wav.exists():
            absent.append(stem)
        elif audio_sha256(wav) != sha:
            mismatched.append(stem)
    errs = []
    if absent:
        errs.append(f'{len(absent)} {what} windows have no audio on disk to '
                    f'verify (e.g. {absent[:3]})')
    if mismatched:
        errs.append(f'{len(mismatched)} {what} windows do not match their '
                    f'stamped audio_sha256 — the audio on disk and the audio '
                    f'the sidecar describes are different files '
                    f'(e.g. {mismatched[:3]})')
    return errs


def negative_transitions(results, windows, stratum, short, long_, kind=None):
    """(items, b, r) — new bluffs, recovered abstentions, over one stratum.

    `kind` additionally restricts to one `candidate_kind`. The pooled bound is
    a bound on the design mixture (26 free-form : 21 opening : 4 unidentified),
    and those weights came from sampling quotas and labeling yield, not from
    product prevalence — so the per-source split is not a diagnostic nicety,
    it is what makes the number interpretable.
    """
    answered = defaultdict(dict)
    for res in results:
        meta = windows.get(Path(res.get('file', '')).stem)
        if not meta or meta.get('stratum') != stratum:
            continue
        if kind is not None and meta.get('candidate_kind') != kind:
            continue
        answered[meta['item']][meta['window_seconds']] = int(
            res.get('composition_confidence') != 'none')
    items = sorted(i for i, d in answered.items() if short in d and long_ in d)
    b = sum(1 for i in items if answered[i][long_] > answered[i][short])
    r = sum(1 for i in items if answered[i][long_] < answered[i][short])
    return items, b, r, answered


def report_unknown_sensitivity(side, b, n, boundary_pp, per_source=()):
    """Worst case if every `unknown` item was a no-sahitya window that bluffed.

    The unknowns are **informative missingness, not random loss**: one is
    `unusable` — the very property that could conceal singing — and the blank
    sits mid-sheet with labeling continuing after it. Dropping them silently
    assumes they would have behaved like the items that were labelable, which
    is the assumption least favourable to catching a problem. The observed
    bound stays the headline; this sits next to it, never buried.

    The sensitivity is reported under the **applied** gate as well as pooled.
    A pooled worst case that reads "still safe" says nothing about rule A: two
    unknowns split one per gating source move each of those sources to b=1,
    which is exactly what rule A refuses to tolerate.
    """
    by_kind = Counter(m.get('candidate_kind') for m in side['windows'].values()
                      if m.get('stratum') == 'unknown'
                      and m['window_seconds'] == max(side['durations']))
    k = sum(by_kind.values())
    if not k:
        return
    ub_worst = 100 * clopper_pearson_upper(b + k, n + k)
    print(f'\n  worst case on the {k} unknown item(s) — if every one was a '
          f'no-sahitya window')
    print(f'  that bluffed: pooled b={b + k}/n={n + k}, one-sided 95% upper '
          f'bound {ub_worst:.1f}pp '
          f'{"(still safe)" if ub_worst < boundary_pp else "(NOT safe)"}')
    if per_source:
        worst = [(kind, sn + by_kind.get(kind, 0), sb + by_kind.get(kind, 0),
                  100 * clopper_pearson_upper(sb + by_kind.get(kind, 0),
                                              sn + by_kind.get(kind, 0)))
                 for kind, sn, sb, _r, _ub in per_source
                 if sn >= SOURCE_MIN_N]
        held = all(ub < boundary_pp for _k, _n, _b, ub in worst)
        print('  under the APPLIED gate (rule A), same worst case: '
              + '; '.join(f'{kind} b={wb}/n={wn} UB {ub:.1f}pp'
                          for kind, wn, wb, ub in worst)
              + f' -> {"still safe" if held else "NOT safe"}')
    print('  These are informative missingness, not random loss: `unusable` is '
          'exactly the')
    print('  property that can conceal singing. The observed bound above is '
          'the headline;')
    print('  this is the sensitivity, and both belong in any quoted result.')


def report_by_source(results, windows, short, long_, boundary_pp):
    """Per-`candidate_kind` readout of the gating stratum. Returns its rows.

    `DURATION_PROBE_PREREGISTRATION.md` §6 has promised since 2026-07-28 that
    "each source is also reported alone"; the scorer grouped on `stratum` only
    and never delivered it. Without this split a failure concentrated in one
    source hides inside the pooled bound: 3 new bluffs all landing in one place
    reads 3/51 -> 14.5pp SAFE pooled, while free-form alone is 3/26 -> 27.2pp.
    """
    kinds = sorted({m.get('candidate_kind') for m in windows.values()
                    if m.get('stratum') == GATING_STRATUM
                    and m.get('candidate_kind')})
    out = []
    for kind in kinds:
        items, b, r, _ = negative_transitions(results, windows,
                                              GATING_STRATUM, short, long_,
                                              kind=kind)
        if items:
            out.append((kind, len(items), b, r,
                        100 * clopper_pearson_upper(b, len(items))))

    print(f'\n--- GATING STRATUM BY SOURCE (pre-registration §6: "each source '
          f'is also reported alone") ---')
    if not out:
        print('  (gating stratum is empty)')
        return out
    print(f"  {'source':<24} {'n':>4} {'b':>3} {'r':>3} {'UB':>8}   "
          f"what that n could rule out at b=0,1,2")
    for kind, n, b, r, ub in out:
        heads = '  '.join(f'b={bb}:{uu:5.1f}{"" if ok else "*"}'
                          for bb, uu, ok in power_table(n, boundary_pp)[:3])
        print(f'  {kind:<24} {n:>4} {b:>3} {r:>3} {ub:>7.1f}pp   {heads}')
    print('  (* = that many new bluffs would NOT rule out the boundary)')
    print('  The pooled bound is a bound on the DESIGN MIXTURE — these '
          'weights came from')
    print('  sampling quotas and labeling yield, not from product prevalence.')
    return out


def source_gate_verdict(per_source, boundary_pp, registered_counts=None):
    """The applied safety gate — rule A. -> (safety_holds, reason).

    `DURATION_PROBE_PREREGISTRATION.md` §6b, frozen by Deepti 2026-07-29: SAFE
    requires the one-sided exact 95% upper bound below the boundary for every
    source with n >= SOURCE_MIN_N. Sources below that n are reported but cannot
    carry a claim, and cannot grant one either — a mixture with no registered
    weights is not the estimand, so the pooled bound no longer decides
    anything.

    `registered_counts` is the gating-source census *before* any §5b exclusion.
    An exclusion that pushes a registered source below SOURCE_MIN_N changes what
    the conjunction is quantified over: the source silently stops carrying a
    bound and the survivors grant a SAFE the design never authorised. That is
    the same hole `_verify_gating_sources()` closes for a source that goes
    missing, so it suppresses here rather than passing quietly.
    """
    realized = {row[0]: row[1] for row in per_source}
    shrunk = [(k, n, realized.get(k, 0))
              for k, n in sorted((registered_counts or {}).items())
              if n >= SOURCE_MIN_N and realized.get(k, 0) < SOURCE_MIN_N]
    if shrunk:
        return False, ('exclusions dropped ' + ', '.join(
            f'{k} {n}->{r}' for k, n, r in shrunk)
            + f' below n>={SOURCE_MIN_N}; rule A cannot be quantified over the '
              f'remaining sources')
    major = [row for row in per_source if row[1] >= SOURCE_MIN_N]
    if not major:
        return False, f'no source reaches n>={SOURCE_MIN_N}'
    failed = [(k, ub) for k, _n, _b, _r, ub in major if ub >= boundary_pp]
    if failed:
        return False, ', '.join(f'{k} UB {ub:.1f}pp' for k, ub in failed)
    return True, ', '.join(f'{k} UB {ub:.1f}pp' for k, _n, _b, _r, ub in major)


def report_negatives(args, boundary_pp: float,
                     audio_dir: Path | None = None) -> tuple[bool, str]:
    """Print the negative arm and return (safety_holds, one-line reason).

    Strata stay separate (`METRIC_CONTRACT`): a no-sahitya window carries no
    sahitya to find at any length, while a sung work we do not hold fails for a
    different reason. Only the no-sahitya stratum gates, because it is the only
    one whose truth is established — see `SENSITIVITY_STRATA`.
    """
    results = json.loads(Path(args.negative_results).read_text())
    side = json.loads(Path(args.negative_truth).read_text())
    errs = validate_negatives(results, side, audio_dir)

    # §5b exclusions, applied only after the FULL arm has been validated, so a
    # reduced run can never look more complete than it is. The pre-exclusion
    # gating census is kept: rule A is quantified over the sources the design
    # registered, not over whatever survives.
    excluded = set(getattr(args, 'exclude_item', None) or [])
    registered_gating = dict(side.get('gating_source_counts') or {})
    registered_n_items = side.get('n_items')
    if excluded:
        results, side, x_errs = apply_exclusions(results, side, excluded,
                                                 'item', 'negative item')
        errs += x_errs
        if not x_errs:
            # Re-validate the reduced arm against its RECOMPUTED bookkeeping.
            # The audio was hashed on the full pass and exclusion removes rows
            # rather than touching bytes, so it is not re-hashed here.
            errs += validate_negatives(results, side, audio_dir,
                                       verify_audio=False)
        exclusion_block('negative arm, pre-registration §5b', excluded,
                        getattr(args, 'exclude_reason', None) or '(none given)',
                        registered_n_items,
                        len({m['item'] for m in side['windows'].values()}))
    windows = side['windows']

    counts = Counter(m.get('stratum') for m in windows.values()
                     if m['window_seconds'] == max(side['durations']))
    print('\n--- NEGATIVE ARM (sahitya adjudicated by ear on the scored '
          f'{max(side["durations"])}s window) ---')
    print('  strata: ' + ', '.join(f'{k} {v}' for k, v in sorted(
        counts.items(), key=lambda kv: str(kv[0]))))
    if errs:
        print('  ===== NEGATIVE ARM INVALID =====')
        for e in errs:
            print(f'    ! {e}')

    short, long_ = min(side['durations']), max(side['durations'])
    rows = []
    for stratum in (GATING_STRATUM,) + SENSITIVITY_STRATA:
        items, b, r, answered = negative_transitions(results, windows, stratum,
                                                     short, long_)
        if not items:
            continue
        a_s = sum(answered[i][short] for i in items)
        a_l = sum(answered[i][long_] for i in items)
        rows.append((stratum, items, b, r, a_s, a_l))

    print(f"\n{'stratum':>20} {'n':>4} {f'ans@{short}s':>9} "
          f"{f'ans@{long_}s':>10} {'new bluffs':>11} {'recovered':>10} "
          f"{'net':>8}")
    for stratum, items, b, r, a_s, a_l in rows:
        n = len(items)
        print(f'{stratum:>20} {n:>4} {a_s:>9} {a_l:>10} {b:>11} {r:>10} '
              f'{100.0 * (b - r) / n:>+7.1f}pp')
    if not rows:
        print('  (no stratum has paired windows at both endpoints)')

    gate = next((x for x in rows if x[0] == GATING_STRATUM), None)
    per_source = report_by_source(results, windows, short, long_, boundary_pp)

    print(f'\n--- FROZEN NEGATIVE DECISION RULE (boundary '
          f'{boundary_pp:+.0f}pp) ---')
    print('  Estimand: the change in ANSWER rate, 30s -> 300s, among windows '
          'her ear')
    print('  confirmed carry no sung words. Statistic: b = items that abstain '
          'at 30s and')
    print('  answer at 300s. Rule A (§6b): SAFE if the one-sided exact 95% '
          'upper bound on')
    print(f'  b/n is below the boundary in EVERY source with n>='
          f'{SOURCE_MIN_N}. The pooled bound below')
    print('  is reported for context and gates nothing. Reverse flips are '
          'ignored, which can')
    print('  only make it stricter.')
    if errs:
        print('  SUPPRESSED — the negative arm did not validate.')
        return False, 'negative arm invalid'
    if not gate:
        print(f'  SUPPRESSED — the {GATING_STRATUM} stratum is empty.')
        return False, 'no gating negative stratum'
    _, items, b, r, _, _ = gate
    n = len(items)
    ub = 100 * clopper_pearson_upper(b, n)
    print(f'  n={n}  b={b}  (r={r} recovered)  one-sided 95% upper bound '
          f'{ub:.1f}pp')
    for bb, uu, ok in power_table(n, boundary_pp):
        print(f'    had b been {bb}: UB {uu:5.1f}pp '
              f'{"(safe)" if ok else "(NOT safe)"}')

    report_unknown_sensitivity(side, b, n, boundary_pp, per_source)

    # ---- rule A decides; the pooled bound is reported beside it and gates
    # nothing. Frozen by Deepti 2026-07-29, DURATION_PROBE_PREREGISTRATION §6b.
    pooled_safe = ub < boundary_pp
    src_safe, src_why = source_gate_verdict(per_source, boundary_pp,
                                            registered_gating)
    print('\n--- APPLIED GATE: RULE A, source-specific conjunction (§6b, '
          'frozen 2026-07-29) ---')
    print(f'  A  APPLIED  source-specific     -> '
          f'{"SAFE" if src_safe else "NOT ESTABLISHED"}  ({src_why})')
    print(f'     every source with n>={SOURCE_MIN_N} must clear the boundary '
          f'alone. Strict, but it is the')
    print('     only reading that means anything without registered mixture '
          'weights.')
    print(f'  B  REPORTED, NOT GATING  pooled -> '
          f'{"would say SAFE" if pooled_safe else "would say NOT ESTABLISHED"}'
          f'  (UB {ub:.1f}pp on n={n})')
    print('     valid, but bounds the design mixture and nothing else, and no '
          'argument for')
    print('     those weights is registered. It decides nothing here.')
    if pooled_safe and not src_safe:
        print('  !! THE POOLED BOUND WOULD HAVE PASSED THIS RUN AND RULE A '
              'DOES NOT.')
        print('     This is the exact case the gate exists for: a bluff rise '
              'concentrated in one')
        print('     source, hidden by the mixture. The verdict is NOT '
              'ESTABLISHED.')
    elif src_safe and not pooled_safe:
        print('  !! rule A passes while the pooled bound does not — read the '
              'per-source table')
        print('     above before quoting anything; this ordering is unusual.')

    if src_safe:
        print(f'\n  APPLIED (rule A): SAFE — a bluff rise of '
              f'{boundary_pp:+.0f}pp or more is ruled out in every gating '
              f'source.')
        return True, f'rule A: {src_why} (pooled {ub:.1f}pp, not gating)'
    print(f'\n  APPLIED (rule A): NOT SAFE — {src_why}. This does NOT mean '
          f'bluffing rose — it means this arm cannot say it did not.')
    return False, f'rule A: {src_why} (pooled {ub:.1f}pp, not gating)'


if __name__ == '__main__':
    main()
