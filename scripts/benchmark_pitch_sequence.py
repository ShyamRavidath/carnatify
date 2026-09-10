"""Fixed 20-epoch temporal baseline on the existing source-group folds.

No early stopping or hyperparameter selection from held-out folds. A single
fold is a compute/learning smoke check, not a complete cross-validation score.
"""
import argparse,json,sys,time
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
import torch
from scripts.raga_pipeline import sha,write_json,load_features
from carnatify.ml.melody_features import feature_vector
from carnatify.ml.pitch_sequence import sequence_features,PitchTemporalConv,VERSION


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,default=ROOT/'data/overhaul/combined')
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/pitch_sequence')
    ap.add_argument('--fold',type=int,choices=range(5),default=0)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(4);torch.manual_seed(42);np.random.seed(42)
    z=load_features(args.run);manifest=json.loads((args.run/'manifest.json').read_text())
    cache=args.out/'features.npz';digest=sha(args.run/'features.npz');started=time.monotonic()
    if cache.exists():
        with np.load(cache) as data:
            if str(data['base_sha256'])!=digest or str(data['version'])!=VERSION:
                raise ValueError('Sequence cache contract mismatch')
            X=data['X']
    else:
        by_track={r['track']:r for r in manifest['rows']};sequences={}
        for track in dict.fromkeys(z['track']):
            row=by_track[str(track)];path=ROOT/row['contour']
            if sha(path)!=row['contour_sha256']:raise ValueError('Source contour changed')
            f=np.load(path) if path.suffix=='.npy' else np.loadtxt(path)[:,1]
            width=round(60/row['hop_s']);parts=[]
            for start in sorted({round(max(0,len(f)-width)*q) for q in (.2,.5,.8)}):
                clip=f[start:start+width]
                if np.sum(np.isfinite(clip)&(clip>0))*row['hop_s']<10:continue
                if feature_vector(clip,row['tonic'],row['hop_s'],'elapsed') is None:continue
                parts.append(sequence_features(clip,row['tonic'],row['hop_s']))
            if len(parts)!=sum(z['track']==track):raise ValueError('Window alignment mismatch')
            sequences[str(track)]=iter(parts)
        X=np.stack([next(sequences[str(t)]) for t in z['track']])
        np.savez_compressed(cache,X=X,base_sha256=digest,version=VERSION)
    classes,y=np.unique(z['y'],return_inverse=True)
    fold_path=args.run/'folds.json'
    fold_document=json.loads(fold_path.read_text())
    if fold_document['feature_sha256']!=digest:raise ValueError('Fold assignment belongs to different features')
    fold_map=fold_document['folds']
    folds=np.array([fold_map[str(t)] for t in z['track']]);tr=np.flatnonzero(folds!=args.fold);te=np.flatnonzero(folds==args.fold)
    if set(z['group'][tr])&set(z['group'][te]):raise ValueError('Source group leakage')
    tracks=Counter(z['track'][tr]);class_tracks=Counter()
    for tid in tracks:class_tracks[str(z['y'][np.flatnonzero(z['track']==tid)[0]])]+=1
    weights=np.array([1/(tracks[z['track'][i]]*class_tracks[str(z['y'][i])]) for i in tr])
    weights/=weights.mean();weight_by_row=np.zeros(len(X),dtype=np.float32);weight_by_row[tr]=weights
    Xt=torch.from_numpy(X);yt=torch.from_numpy(y);wt=torch.from_numpy(weight_by_row)
    model=PitchTemporalConv(len(classes));optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.001)
    generator=np.random.default_rng(42)
    report=dict(status='single fixed source-held-out fold; development temporal baseline, not complete CV',
                fold=args.fold,epochs=20,seed=42,feature_version=VERSION,
                base_feature_sha256=digest,fold_sha256=sha(fold_path),classes=classes.tolist(),n_train_windows=len(tr),
                n_test_windows=len(te),history=[])
    for epoch in range(20):
        model.train();loss_sum=0.
        for batch in np.array_split(generator.permutation(tr),max(1,int(np.ceil(len(tr)/32)))):
            optimizer.zero_grad(set_to_none=True)
            loss=(torch.nn.functional.cross_entropy(model(Xt[batch]),yt[batch],reduction='none')*wt[batch]).mean()
            if not torch.isfinite(loss):raise ValueError('Non-finite sequence loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step()
            loss_sum+=float(loss.detach())*len(batch)
        model.eval();probabilities=[]
        with torch.no_grad():
            for batch in np.array_split(te,max(1,int(np.ceil(len(te)/64)))):
                probabilities.append(model(Xt[batch]).softmax(1).numpy())
        p=np.concatenate(probabilities);test_tracks=z['track'][te]
        unique,first=np.unique(test_tracks,return_index=True)
        averaged=np.stack([p[test_tracks==tid].mean(0) for tid in unique])
        result=dict(epoch=epoch+1,train_loss=loss_sum/len(tr),
                    track_top1=float(np.mean(averaged.argmax(1)==y[te][first])),elapsed_s=time.monotonic()-started)
        report['history'].append(result);write_json(args.out/f'fold_{args.fold}.json',report)
        print(json.dumps(result),flush=True)
    np.savez_compressed(args.out/f'fold_{args.fold}_predictions.npz',probabilities=p,track=test_tracks,y=y[te],classes=classes)
    torch.save(dict(state_dict=model.state_dict(),classes=classes.tolist(),feature_version=VERSION,
                    training_track_ids=np.unique(z['track'][tr]).tolist()),args.out/f'fold_{args.fold}.pt')


if __name__=='__main__':main()
