"""Synthetic local-GPU gradient sanity check; never saves trained weights."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['HF_HOME']=str(ROOT/'data/overhaul/cache/huggingface')
sys.path[:0]=[str(ROOT/'data/overhaul/runtime_deps'),str(ROOT),str(ROOT/'src')]
import numpy as np
import torch
from carnatify.audio.musicfm_frontend import MusicFM,HASHES
from scripts.raga_pipeline import write_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--device',choices=['cpu','mps'],default='mps')
    args=parser.parse_args()
    torch.set_num_threads(4);torch.manual_seed(42)
    torch.autograd.set_detect_anomaly(True)
    sr=24000;t=np.arange(sr*10)/sr
    hz=220*2**((np.sin(t*.7)+.05*np.sin(t*25))/12)
    phase=2*np.pi*np.cumsum(hz)/sr
    y=(.2*np.sin(phase)+.07*np.sin(2*phase)+.03*np.sin(2*np.pi*110*t)).astype(np.float32)
    out=ROOT/f'data/overhaul/musicfm_{args.device}_gradient_boundary_diagnostic'
    plan=dict(waveform_sha256=hashlib.sha256(y.tobytes()).hexdigest(),audio='synthetic 10s; no real recording',
        artifacts=HASHES,layer=7,trainable_encoder_block=6,head_classes=5,synthetic_target=0,
        steps=3,optimizer='SGD',head_lr=.01,block_lr=.0001,device=args.device,save_weights=False,
        convolution_output_gradient='contiguous',parameter_check='max_change_across_all_block_parameters',
        gradient_diagnostics='cpu_float64_per_parameter_and_device_norm',frozen_boundary_input_gradient=True)
    if (out/'plan.json').exists() and json.loads((out/'plan.json').read_text())!=plan:
        raise ValueError('Gradient probe plan changed')
    write_json(out/'plan.json',plan)
    model=MusicFM(ROOT/'data/overhaul/models/musicfm',device=args.device)
    block=model.core.conformer.layers[6];block.requires_grad_(True)
    # Request an input gradient at the frozen-prefix boundary. The local MPS
    # affine-only LayerNorm backward produced wrong gradients in the control.
    def boundary_gradient(module, inputs):
        x,*rest=inputs
        return (x.detach().requires_grad_(True),*rest)
    block.register_forward_pre_hook(boundary_gradient)
    # The local MPS Conv1d backward rejects a transposed incoming gradient.
    # Materialize its layout without changing values or the forward operation.
    def contiguous_gradient(module, inputs, output):
        if output.requires_grad:
            output.register_hook(lambda gradient: gradient.contiguous())
    for module in block.modules():
        if isinstance(module,torch.nn.Conv1d):
            module.register_forward_hook(contiguous_gradient)
    head=torch.nn.Linear(1024,5).to(args.device)
    optimizer=torch.optim.SGD([dict(params=head.parameters(),lr=.01),dict(params=block.parameters(),lr=.0001)])
    before=[p.detach().cpu().clone() for p in block.parameters()]
    steps=[]
    for step in range(3):
        begin=time.monotonic();optimizer.zero_grad(set_to_none=True)
        features=model.hidden_tensor(y,sr,layer=7).mean(0)
        logits=head(features)[None]
        loss=torch.nn.functional.cross_entropy(logits,torch.tensor([0],device=args.device))
        loss.backward()
        grads=[p.grad for p in block.parameters() if p.grad is not None]
        if not grads or not all(bool(torch.isfinite(g).all()) for g in grads):
            raise ValueError('Missing/nonfinite encoder gradients')
        norm=float(torch.linalg.vector_norm(torch.cat([g.flatten() for g in grads])).item())
        if norm<=0:raise ValueError('Zero encoder gradient')
        cpu_norms={name:float(torch.linalg.vector_norm(p.grad.detach().cpu().double()))
                   for name,p in block.named_parameters() if p.grad is not None}
        cpu_norm=float(np.linalg.norm(list(cpu_norms.values())))
        if not np.isfinite(cpu_norm) or cpu_norm<=0:raise ValueError('Invalid CPU-verified gradient')
        optimizer.step()
        if args.device=='mps':torch.mps.synchronize()
        steps.append(dict(step=step,loss=float(loss.item()),encoder_gradient_norm=norm,
                          encoder_gradient_cpu_float64_norm=cpu_norm,parameter_gradient_norms=cpu_norms,
                          parameters_with_gradient=len(grads),elapsed_s=time.monotonic()-begin))
        print(steps[-1],flush=True)
    delta=max(float(torch.max(torch.abs(p.detach().cpu()-old))) for p,old in zip(block.parameters(),before))
    if delta<=0 or steps[-1]['loss']>=steps[0]['loss']:
        raise ValueError('Sanity optimization did not update/reduce loss')
    report=dict(steps=steps,checked_parameter_max_abs_change=delta,
                status='Synthetic one-example gradient sanity only; no semantic accuracy or saved weights')
    write_json(out/'result.json',report)


if __name__=='__main__':main()
