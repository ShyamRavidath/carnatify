"""Package an uncalibrated conditional vocabulary candidate; no fitting."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import joblib
from scripts.raga_pipeline import sha,write_json
from carnatify.ml.vocabulary_cascade import VocabularyCascade


def main():
    base=ROOT/'data/overhaul';paths=[base/'combined/raga_ridge.joblib',base/'broader/raga.joblib']
    narrow,broad=[joblib.load(p) for p in paths]
    if narrow['feature_version']!=broad['feature_version']:raise ValueError('Feature versions differ')
    model=VocabularyCascade(narrow['model'],broad['model']);out=base/'cascade';out.mkdir(parents=True,exist_ok=True)
    inputs={str(p.relative_to(ROOT)):sha(p) for p in paths}
    bundle=dict(model=model,representation='voiced',feature_version=narrow['feature_version'],inputs=inputs,
        training_track_ids=sorted(set(narrow.get('training_track_ids',[]))|set(broad.get('training_track_ids',[]))),
        status='fixed conditional vocabulary combination; uncalibrated development candidate',
        calibration=dict(status='uncalibrated combination',gate=dict(threshold=1.000001)))
    joblib.dump(bundle,out/'raga.joblib')
    write_json(out/'model.json',dict(inputs=inputs,classes=model.classes_.tolist(),model_sha256=sha(out/'raga.joblib'),
        status=bundle['status']))


if __name__=='__main__':main()
