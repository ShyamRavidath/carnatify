"""Compare legacy training contours/tonics with exact-window inference DSP.

Training-only diagnostic, not accuracy or a claim either tonic is ground truth.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('OMP_NUM_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json
from carnatify.audio.melody_frontend import extract_query,HOP_S,VERSION
from carnatify.ml.melody_features import feature_vector


def compare(row):
    if sha(ROOT/row['audio'])!=row['audio_sha256'] or sha(ROOT/row['contour'])!=row['contour_sha256']:
        raise ValueError('Training input changed')
    original=np.load(ROOT/row['contour']);hop=row['hop_s'];width=round(60/hop)
    start=round(max(0,len(original)-width)*.5);legacy=original[start:start+width]
    f,metadata=extract_query(ROOT/row['audio'],row['audio_sha256'],start*hop,min(60,len(legacy)*hop),
        ROOT/'data/overhaul/cache/training_context')
    result=dict(track=row['track'],label=row['label'],group=row['group'],start_s=start*hop,
        legacy_tonic_hz=row['tonic'],query_tonic_hz=metadata['tonic_hz'],query_metadata=metadata)
    if row['tonic'] and metadata['tonic_hz']:
        result['tonic_pitch_class_difference_cents']=float(abs((1200*np.log2(metadata['tonic_hz']/row['tonic'])+600)%1200-600))
    indices=np.rint(np.arange(len(f))*HOP_S/hop).astype(int);valid=indices<len(legacy)
    reference=legacy[indices[valid]];live=f[valid];both=(reference>0)&(live>0)
    result['jointly_voiced_frames']=int(both.sum())
    if both.any():
        cents=abs((1200*np.log2(live[both]/reference[both])+600)%1200-600)
        result['pitch_class_agreement_50c']=float(np.mean(cents<50))
    a=feature_vector(legacy,row['tonic'],hop,'voiced')
    b=feature_vector(f,metadata['tonic_hz'],HOP_S,'voiced') if metadata['tonic_hz'] else None
    if a is not None and b is not None:
        result['feature_cosine']=float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)))
    return result


def main():
    source=ROOT/'data/overhaul/file_tag_guarded/manifest.json'
    identity=ROOT/'data/overhaul/repro_audio_identity/audio_identity.json'
    evidence=ROOT/'data/overhaul/repro_audio_identity/file_raga_evidence.json'
    identities={r['track']:r for r in json.loads(identity.read_text())['rows']}
    supported={r['track'] for r in json.loads(evidence.read_text())['rows'] if r['status']=='file_tag_consistent'}
    rows=[r for r in json.loads(source.read_text())['rows'] if r['track'] in supported]
    rows=sorted(rows,key=lambda r:hashlib.sha256(r['track'].encode()).hexdigest())[:24]
    rows=[dict(r,audio_sha256=identities[r['track']]['sha256']) for r in rows]
    out=ROOT/'data/overhaul/training_context_diagnostic'
    plan=dict(inputs={str(p.relative_to(ROOT)):sha(p) for p in (source,identity,evidence,Path(__file__))},
        rows=rows,selection='first 24 SHA256(track)-ordered file-tag-consistent training recordings',
        query='exact central legacy training 60s interval; independently estimated query tonic',frontend=VERSION)
    pp=out/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Diagnostic plan changed')
    write_json(pp,plan);results=[]
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
        for result in pool.map(compare,rows):
            results.append(result);write_json(out/'progress.json',dict(plan_sha256=sha(pp),rows=results))
            print(f'{len(results)}/{len(rows)} {result["track"]}',flush=True)
    summary={key:dict(n=sum(key in r for r in results),median=float(np.median([r[key] for r in results if key in r])))
             for key in ('tonic_pitch_class_difference_cents','pitch_class_agreement_50c','feature_cosine')
             if any(key in r for r in results)}
    write_json(out/'result.json',dict(plan_sha256=sha(pp),rows=results,summary=summary,
        limitation='Training-only context mismatch diagnostic; neither frontend is independent ground truth'))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
