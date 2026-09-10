"""Quarantine non-clean audio without changing retained features or labels."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.extract_context_training import filter_decode_audit
from scripts.raga_pipeline import load_features,sha,write_json
from carnatify.audio.cache_io import atomic_npz


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--identity',type=Path,required=True)
    p.add_argument('--decode-audit',type=Path,required=True)
    args=p.parse_args()
    if args.out.resolve()==args.run.resolve():raise ValueError('Use a separate output run')
    source=json.loads((args.run/'manifest.json').read_text())
    identity={r['track']:r for r in json.loads(args.identity.read_text())['rows']}
    rows=[]
    for row in source['rows']:
        if row.get('corpus')=='archive':
            evidence=identity[row['track']]
            if row['audio']!=evidence['audio'] or sha(ROOT/row['audio'])!=evidence['sha256']:
                raise ValueError('Stale raw audio identity')
            row=dict(row,audio_sha256=evidence['sha256'])
        rows.append(row)
    kept,excluded=filter_decode_audit(rows,json.loads(args.decode_audit.read_text()))
    plan=dict(inputs={str(f.resolve()):sha(f) for f in (args.run/'manifest.json',args.run/'features.npz',
        args.identity,args.decode_audit,Path(__file__),ROOT/'scripts/extract_context_training.py')},
        policy='only strict-clean archival audio; retain reference-pitch CompMusic',excluded=excluded)
    target=args.out/'plan.json'
    if target.exists() and json.loads(target.read_text())!=plan:raise ValueError('Frozen filter plan changed')
    write_json(target,plan)
    z=load_features(args.run);mask=np.isin(z['track'],[r['track'] for r in kept])
    manifest=args.out/'manifest.json'
    write_json(manifest,dict(source,rows=kept,decode_filter_plan_sha256=sha(target)))
    values={key:z[key][mask] for key in ('X','legacy','y','track','group')}
    atomic_npz(args.out/'features.npz',**values,version=z['version'],manifest_sha256=sha(manifest))
    # Preserve the pre-existing development assignment for a matched ablation.
    folds=args.run/'folds.json'
    if folds.exists():
        old=json.loads(folds.read_text())
        if old['feature_sha256']!=sha(args.run/'features.npz'):raise ValueError('Stale source folds')
        write_json(args.out/'folds.json',dict(old,feature_sha256=sha(args.out/'features.npz'),
            parent_folds_sha256=sha(folds),folds={t:f for t,f in old['folds'].items() if t in set(values['track'])}))
    print(json.dumps(dict(tracks=len(kept),windows=int(mask.sum()),excluded=len(excluded))))


if __name__=='__main__':main()
