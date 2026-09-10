"""Fit the measured kernel recognizer with OOF temperature/coverage metadata."""
from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import joblib
from threadpoolctl import threadpool_limits
from carnatify.ml.distribution_classifier import DistributionSVC,DistributionKernelRidge
from carnatify.ml.melody_features import FEATURE_VERSIONS
from carnatify.ml.calibration import fit_temperature,temperature_scale,selective_threshold
from carnatify.ml.evaluation_integrity import training_support
from scripts.raga_pipeline import load_features,sha,write_json


def training_window_seconds(manifest):
    if 'context_plan_sha256' not in manifest:return 60
    value=manifest.get('protocol',{}).get('window_s')
    if type(value) is not int or value not in (60,180):
        raise ValueError('Missing or invalid context-training window metadata')
    return value


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,default=ROOT/'data/architecture_audit')
    ap.add_argument('--oof',type=Path,default=ROOT/'data/overhaul/elapsed_hellinger_svc_oof.npz')
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/raga_svc.joblib')
    ap.add_argument('--family',choices=['svc','kernel_ridge'],default='svc')
    ap.add_argument('--representation',choices=['elapsed','voiced'],default='elapsed')
    ap.add_argument('--audio-identity',type=Path,help='Byte audit to verify and embed for archival training rows')
    args=ap.parse_args()
    z=load_features(args.run);o=np.load(args.oof)
    manifest=json.loads((args.run/'manifest.json').read_text())
    window_s=training_window_seconds(manifest)
    training_audio_hashes=[]
    if args.audio_identity:
        identities={r['track']:r for r in json.loads(args.audio_identity.read_text())['rows']}
        for row in manifest['rows']:
            if row.get('corpus')!='archive':continue
            evidence=identities[row['track']]
            if row['audio']!=evidence['audio'] or sha(ROOT/row['audio'])!=evidence['sha256']:
                raise ValueError('Stale archival audio identity audit')
            training_audio_hashes.append(evidence['sha256'])
    if not {'window_p','window_y','window_group'}<=set(o.files):
        raise ValueError('Regenerate kernel OOF with per-window predictions before calibration')
    classes=np.unique(z['y'])
    if not np.array_equal(classes,o['classes']):raise ValueError('OOF vocabulary mismatch')
    if not np.array_equal(z['track'],o['window_track']):raise ValueError('OOF track mismatch')
    expected=dict(source='legacy' if args.representation=='voiced' else 'X',mode='tdms',gamma=2)
    expected.update(C=10) if args.family=='svc' else expected.update(alpha=.1)
    if 'config' not in o or json.loads(str(o['config']))!=expected:
        raise ValueError('OOF classifier configuration mismatch; regenerate OOF')
    if str(o['feature_sha256'])!=sha(args.run/'features.npz'):
        raise ValueError('OOF feature hash mismatch')
    calibration=fit_temperature(o['window_p'],o['window_y'],o['window_group'])
    p=temperature_scale(o['window_p'],calibration['temperature'])
    calibration['gate']=selective_threshold(p,o['window_y'])
    calibration['status']='OOF training calibration; independent validation still required'
    _,inverse,count=np.unique(z['track'],return_inverse=True,return_counts=True)
    weight=1/count[inverse];weight/=weight.mean()
    model_type=DistributionSVC if args.family=='svc' else DistributionKernelRidge
    model=model_type(mode='tdms',temperature=calibration['temperature'])
    X=z['legacy'] if args.representation=='voiced' else z['X']
    with threadpool_limits(limits=4):model.fit(X,z['y'],sample_weight=weight)
    version=FEATURE_VERSIONS[args.representation]
    support=training_support(z['y'],z['track'],z['group'])
    bundle=dict(model=model,feature_version=version,representation=args.representation,window_s=window_s,
                feature_sha256=sha(args.run/'features.npz'),manifest_sha256=sha(args.run/'manifest.json'),
                calibration=calibration,training_manifest=str(args.run/'manifest.json'),
                training_track_ids=np.unique(z['track']).tolist(),
                training_audio_sha256=sorted(set(training_audio_hashes)),
                audio_identity_sha256=sha(args.audio_identity) if args.audio_identity else None,
                audio_identity_scope='archival raw audio only; pitch-only CompMusic has no raw-byte receipt',
                class_support=support,
                status='measured development candidate; no SOTA claim')
    if 'context_plan_sha256' in manifest:
        bundle['training_context_plan_sha256']=manifest['context_plan_sha256']
        bundle['training_query_protocol']=manifest['protocol']
    if 'decoder_recovery_plan_sha256' in manifest:
        bundle['training_decoder_recovery_plan_sha256']=manifest['decoder_recovery_plan_sha256']
    args.out.parent.mkdir(parents=True,exist_ok=True);joblib.dump(bundle,args.out)
    write_json(args.out.with_suffix('.json'),dict(model_sha256=sha(args.out),classes=classes.tolist(),
              feature_version=version,calibration=calibration,class_support=support))
    print(json.dumps(calibration,indent=2))


if __name__=='__main__':main()
