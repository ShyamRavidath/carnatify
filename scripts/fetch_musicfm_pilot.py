"""Fetch a pinned public MusicFM-MSD pilot bundle; never execute downloaded code."""
import hashlib
import json
from pathlib import Path
import sys
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.raga_pipeline import write_json
SOURCE='b83ebedb401bcef639b26b05c0c8bee1dc2dfe71'
WEIGHTS='4513b38bc25ad1d227b1980819b9691ba97f4d87'
CONFIG='6b36ef01c6443c67ae7ed0822876d091ab50e4aa'
WEIGHT_SHA='218b483a0256ddef736267425fabb166fd97008983696bb9270def464b47bded'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    out=ROOT/'data/overhaul/models/musicfm';out.mkdir(parents=True,exist_ok=True)
    assets={f'musicfm/{p}':(f'https://raw.githubusercontent.com/minzwon/musicfm/{SOURCE}/{p}',None)
            for p in ['LICENSE','model/musicfm_25hz.py','modules/random_quantizer.py',
                      'modules/features.py','modules/conv.py']}
    assets.update({
        'msd_stats.json':(f'https://huggingface.co/minzwon/MusicFM/resolve/{WEIGHTS}/msd_stats.json',None),
        'config.json':(f'https://huggingface.co/facebook/wav2vec2-conformer-rope-large-960h-ft/resolve/{CONFIG}/config.json',None),
        'pretrained_msd.pt':(f'https://huggingface.co/minzwon/MusicFM/resolve/{WEIGHTS}/pretrained_msd.pt',WEIGHT_SHA)})
    receipt=out/'manifest.json'
    prior=json.loads(receipt.read_text()) if receipt.exists() else {'assets':{}}
    result=dict(source_commit=SOURCE,weights_commit=WEIGHTS,config_commit=CONFIG,assets={})
    for name,(url,expected) in assets.items():
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
        previous=prior['assets'].get(name)
        if target.exists():
            actual=digest(target)
            if actual!=(expected or (previous or {}).get('sha256')):
                raise ValueError(f'Unverified existing artifact: {name}')
        else:
            partial=target.with_suffix(target.suffix+'.partial')
            offset=partial.stat().st_size if partial.exists() else 0
            with requests.get(url,headers={'Range':f'bytes={offset}-'} if offset else {},
                              stream=True,timeout=(15,60)) as response:
                response.raise_for_status()
                if response.status_code==206:
                    if not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'):
                        raise ValueError('Unexpected resume offset')
                    mode='ab'
                else:mode='wb'
                with partial.open(mode) as f:
                    for chunk in response.iter_content(1024*1024):
                        f.write(chunk)
                        if f.tell()//(64*1024*1024)!=(f.tell()-len(chunk))//(64*1024*1024):
                            print(f'{name}: {f.tell()/1024**2:.0f} MiB',flush=True)
            actual=digest(partial)
            if expected and actual!=expected:raise ValueError('Publisher checkpoint checksum mismatch')
            partial.replace(target)
        result['assets'][name]=dict(url=url,sha256=actual,bytes=target.stat().st_size)
        write_json(receipt,result)
        print(f'Verified {name}',flush=True)


if __name__=='__main__':main()
