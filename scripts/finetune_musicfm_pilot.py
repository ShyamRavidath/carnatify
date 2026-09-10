"""Fixed five-epoch, connected-group MusicFM block-6 fine-tuning pilot.

Uses the already-inspected 31-recording tonic-normalized development cohort.
No checkpoint selection, held-out tuning, model export, or production claim.
"""
import hashlib
import argparse
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path[:0]=[str(ROOT/'data/overhaul/runtime_deps'),str(ROOT),str(ROOT/'src')]
import numpy as np
import torch
from scripts.raga_pipeline import sha,write_json
from scripts.benchmark_musicfm_raga import groups_for
from carnatify.audio.musicfm_frontend import MusicFM,tonic_normalize_audio
from carnatify.audio.utils import load_audio_window
from carnatify.audio.cache_io import atomic_npz


def contiguous_gradient(module,inputs,output):
    if output.requires_grad:output.register_hook(lambda g:g.contiguous())


def train_weights(labels,classes):
    counts=np.array([sum(y==c for y in labels) for c in classes])
    if (counts==0).any():raise ValueError('A training class has no support')
    return len(labels)/(len(classes)*counts)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--optimizer',choices=['sgd','adamw'],default='sgd')
    parser.add_argument('--epochs',type=int,default=5)
    args=parser.parse_args()
    if not 1<=args.epochs<=50:raise ValueError('Bounded pilot requires 1–50 epochs')
    head_lr,block_lr=(.01,.0001) if args.optimizer=='sgd' else (.001,.00001)
    torch.set_num_threads(4);torch.manual_seed(42)
    base=ROOT/'data/overhaul/musicfm_raga_probe_tonic'
    out=ROOT/f'data/overhaul/musicfm_finetune_pilot_v3_{args.optimizer}_{args.epochs}'
    source=json.loads((base/'plan.json').read_text());queries=source['queries']
    groups=groups_for(queries)
    if groups.tolist()!=source['groups']:raise ValueError('Source grouping changed')
    control=ROOT/'data/overhaul/musicfm_gradient_control.json'
    if not json.loads(control.read_text())['status'].startswith('passed_'):raise ValueError('GPU control failed')
    plan=dict(source_plan_sha256=sha(base/'plan.json'),gradient_control_sha256=sha(control),
        script_sha256=sha(Path(__file__)),queries=queries,groups=groups.tolist(),epochs=args.epochs,
        seed=42,batch_size=4,head_lr=head_lr,block_lr=block_lr,optimizer=args.optimizer,
        weight_decay=.01 if args.optimizer=='adamw' else 0.,gradient_norm_limit=1.,
        class_balance='inverse training-fold frequency; weighted per-example mean',
        trainable_block=6,device='mps',arms=['frozen_head','finetuned_block'],
        policy='connected artist/source leave-one-group-out; fixed final epoch; no tuning or model export',
        backbone_mode='eval: dropout and batch statistics frozen; explicit gradients enabled',
        boundary_requires_grad=True,contiguous_convolution_gradients=True,
        rotary_cache_policy='clone inference-populated positional cache before autograd')
    pp=out/'plan.json'
    if pp.exists() and json.loads(pp.read_text())!=plan:raise ValueError('Frozen pilot plan changed')
    write_json(pp,plan);model=MusicFM(ROOT/'data/overhaul/models/musicfm',device='mps')
    block=model.core.conformer.layers[6]
    prefix=[];frozen=[];valid=[];began=time.monotonic()
    for i,q in enumerate(queries):
        key=hashlib.sha256(q['track'].encode()).hexdigest()
        with np.load(base/(key+'.npz'),allow_pickle=False) as z:
            meta=json.loads(str(z['metadata']));ok=bool(z['embedding_valid'])
        if meta['plan_sha256']!=sha(base/'plan.json') or meta['query']!=q:raise ValueError('Feature provenance changed')
        if sha(ROOT/q['audio'])!=q['audio_sha256']:raise ValueError('Audio changed')
        target=out/'prefix'/(key+'.npz')
        if target.exists():
            with np.load(target,allow_pickle=False) as z:
                if str(z['plan_sha256'])!=sha(pp):raise ValueError('Prefix cache changed')
                x=z['prefix'];e=z['pooled']
        elif ok:
            y,sr,_=load_audio_window(ROOT/q['audio'],q['start_s'],10.,24000)
            y,_=tonic_normalize_audio(y,sr,meta['pitch']['tonic_hz'])
            if hashlib.sha256(y.tobytes()).hexdigest()!=meta['normalized_waveform_sha256']:
                raise ValueError('Normalized query changed')
            captured=[]
            hook=block.register_forward_pre_hook(lambda module,args:captured.append(args[0].detach().cpu().numpy().copy()))
            try:e=model.encode(y,sr,layer=7).mean(0)
            finally:hook.remove()
            x=captured[0][0]
            atomic_npz(target,prefix=x,pooled=e,plan_sha256=sha(pp))
        else:x=np.zeros((250,1024),np.float32);e=np.zeros(1024,np.float32)
        if x.shape!=(250,1024) or e.shape!=(1024,) or not np.isfinite(x).all() or not np.isfinite(e).all():raise ValueError('Invalid prefix')
        prefix.append(x);frozen.append(e);valid.append(ok)
        print(f'prefix {i+1}/{len(queries)} {time.monotonic()-began:.1f}s',flush=True)
    X=torch.tensor(np.stack(prefix),device='mps');E=torch.tensor(np.stack(frozen),device='mps')
    with torch.no_grad():
        positions=model.core.conformer.embed_positions(X[:1]).clone()
        recovered=block(X[:1],relative_position_embeddings=positions)[0].mean(1)[0]
        torch.testing.assert_close(recovered.cpu(),E[0].cpu(),rtol=1e-5,atol=1e-5)
    initial={k:v.detach().cpu().clone() for k,v in block.state_dict().items()}
    for module in block.modules():
        if isinstance(module,torch.nn.Conv1d):module.register_forward_hook(contiguous_gradient)
    labels=np.array([q['raga'] for q in queries]);valid=np.array(valid)
    predictions={arm:[None]*len(queries) for arm in plan['arms']};folds=[]
    for gi,group in enumerate(np.unique(groups)):
        tr=np.flatnonzero((groups!=group)&valid);te=np.flatnonzero((groups==group)&valid)
        classes=np.unique(labels[tr]);targets=torch.tensor([list(classes).index(y) for y in labels[tr]],device='mps')
        weights=torch.tensor(train_weights(labels[tr],classes),dtype=torch.float32,device='mps')
        for arm in plan['arms']:
            torch.manual_seed(42);block.load_state_dict(initial);block.requires_grad_(arm=='finetuned_block')
            head=torch.nn.Linear(1024,len(classes)).to('mps')
            torch.nn.init.zeros_(head.weight);torch.nn.init.zeros_(head.bias)
            parameters=[dict(params=list(head.parameters()),lr=head_lr)]
            if arm=='finetuned_block':parameters.append(dict(params=list(block.parameters()),lr=block_lr))
            optimizer=(torch.optim.SGD(parameters) if args.optimizer=='sgd' else
                       torch.optim.AdamW(parameters,weight_decay=.01,foreach=False))
            trainable=[p for group_params in parameters for p in group_params['params']]
            losses=[];rng=np.random.default_rng(42)
            for epoch in range(args.epochs):
                order=rng.permutation(len(tr));total=0.
                for start in range(0,len(order),4):
                    local=order[start:start+4];indices=tr[local];optimizer.zero_grad(set_to_none=True)
                    if arm=='finetuned_block':
                        x=X[indices.tolist()].detach().requires_grad_(True)
                        features=block(x,relative_position_embeddings=positions)[0].mean(1)
                    else:features=E[indices.tolist()]
                    loss=(torch.nn.functional.cross_entropy(head(features),targets[local.tolist()],reduction='none')*
                          weights[targets[local.tolist()]]).mean()
                    if not bool(torch.isfinite(loss)):raise ValueError('Nonfinite training loss')
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(trainable,1.,error_if_nonfinite=True,foreach=False)
                    optimizer.step();total+=float(loss.item())*len(local)
                losses.append(total/len(tr))
            with torch.no_grad():
                for index in te:
                    features=block(X[index:index+1],relative_position_embeddings=positions)[0].mean(1) if arm=='finetuned_block' else E[index:index+1]
                    predictions[arm][index]=str(classes[int(head(features).argmax().item())])
            folds.append(dict(group=str(group),arm=arm,n_train=len(tr),n_test=len(te),losses=losses))
            write_json(out/'progress.json',dict(plan_sha256=sha(pp),folds=folds,predictions=predictions))
            print(f'fold {gi+1}/{len(np.unique(groups))} {arm} losses={losses} elapsed={time.monotonic()-began:.1f}s',flush=True)
    report=dict(plan_sha256=sha(pp),status='inspected small-cohort grouped development pilot; not production accuracy',
        n=len(queries),groups=len(np.unique(groups)),folds=folds,predictions=predictions,
        correct={arm:sum(p==y for p,y in zip(pred,labels)) for arm,pred in predictions.items()},
        elapsed_s=time.monotonic()-began,weights_saved=False)
    write_json(out/'result.json',report);print(json.dumps(report['correct']),flush=True)


if __name__=='__main__':main()
