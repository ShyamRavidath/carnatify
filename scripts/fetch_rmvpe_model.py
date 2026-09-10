"""Fetch one immutable MIT-tagged RMVPE ONNX artifact; no remote Python code."""
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT/'data/overhaul/runtime_deps'),str(ROOT),str(ROOT/'src')]
os.environ['HF_HUB_DISABLE_XET']='1'
from huggingface_hub import hf_hub_download
from scripts.raga_pipeline import sha,write_json

REVISION='e6d0c1a17da07c33557852f9dfa2bd44cc75737d'
DIGEST='5370e71ac80af8b4b7c793d27efd51fd8bf962de3a7ede0766dac0befa3660fd'


if __name__=='__main__':
    dest=ROOT/'data/overhaul/models/rmvpe'
    path=Path(hf_hub_download(repo_id='lj1995/VoiceConversionWebUI',revision=REVISION,
                             filename='rmvpe.onnx',local_dir=dest,token=False))
    if path.stat().st_size!=361688443 or sha(path)!=DIGEST:
        raise ValueError('RMVPE artifact differs from immutable publisher checksum')
    write_json(dest/'provenance.json',dict(repository='lj1995/VoiceConversionWebUI',revision=REVISION,
        sha256=DIGEST,bytes=361688443,publisher_model_card_license='MIT',
        inference_contract_source='RVC-Project/Retrieval-based-Voice-Conversion-WebUI@81eed5e8f68b6bed1789f682fe78cdd324495afc/infer/rmvpe.py',
        status='local pitch-frontend experiment; not production qualification'))
    print(f'Verified {path}',flush=True)
