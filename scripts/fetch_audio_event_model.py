"""Fetch only immutable public AST config and safetensors for local inference."""
from pathlib import Path
import sys
import os

# The Xet transport stalled with a zero-byte payload in this environment while
# the immutable HTTPS endpoint returned 200 and the expected content length.
os.environ['HF_HUB_DISABLE_XET']='1'

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'data/overhaul/runtime_deps'))
from huggingface_hub import hf_hub_download

if __name__=='__main__':
    dest=ROOT/'data/overhaul/models/audio_events'
    for name in ['config.json','preprocessor_config.json','model.safetensors']:
        path=hf_hub_download(repo_id='MIT/ast-finetuned-audioset-10-10-0.4593',
                            revision='f826b80d28226b62986cc218e5cec390b1096902',filename=name,local_dir=dest,token=False)
        print(path,flush=True)
