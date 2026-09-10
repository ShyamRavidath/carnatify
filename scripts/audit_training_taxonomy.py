"""Re-admit archive labels without fuzzy guesses; preserve all original artifacts.

An exact title join is a provenance candidate, not proof of performance identity.
Conflicting/unresolved candidate tags are quarantined, never auto-relabeled.
Missing title joins remain explicit weak supervision in the permissive cohort.
"""
from __future__ import annotations
import argparse,json,re,sys
from collections import defaultdict,Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from normalize_ragas import fold,build_fold_index,resolve
from scripts.raga_pipeline import sha,write_json


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive-run',type=Path,default=ROOT/'data/architecture_audit')
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/taxonomy_admission.json')
    args=ap.parse_args()
    training=args.archive_run.resolve()/'manifest.json'
    scraped=ROOT/'data/scraped_compositions.json'
    provenance=ROOT/'data/qmax_audit/provenance.json'
    rows=json.loads(training.read_text())['rows']
    vocab=build_fold_index(sorted({r['label'] for r in rows}))
    source=defaultdict(list)
    for r in json.loads(scraped.read_text()):
        source[fold(r['title'])].append(r)
    prov={r['stem']:r for r in json.loads(provenance.read_text())}
    out=[]
    for row in rows:
        p=prov.get(row['track'],{})
        title=re.sub(r'_r\d+$','',p.get('title_stem',''))
        candidates=[r for r in source.get(fold(title),[]) if r.get('raga_canonical')==row['label']]
        tags=sorted({r['raga'] for r in candidates if r.get('raga')})
        resolutions={r:resolve(r,vocab,list(vocab)) for r in tags}
        status=('no_exact_title_provenance' if not tags else
                'strict_tag_consistent' if all(v==row['label'] for v in resolutions.values()) else
                'quarantine_unresolved_or_conflicting_tag')
        out.append(dict(track=row['track'],label=row['label'],title=title,status=status,
                        raw_tags=tags,resolutions=resolutions,
                        source_urls=sorted({r['source_url'] for r in candidates})))
    report=dict(schema=1,policy='exact vocabulary or explicit alias; no fuzzy relabeling',
        inputs={str(p.relative_to(ROOT)):sha(p) for p in [training,scraped,provenance]},
        counts=dict(Counter(r['status'] for r in out)),rows=out,
        limitations='Title candidates can span artists; consistent tags are weak supervision, not verified audio truth.')
    write_json(args.out,report)
    print(json.dumps(report['counts'],indent=2))


if __name__=='__main__':main()
