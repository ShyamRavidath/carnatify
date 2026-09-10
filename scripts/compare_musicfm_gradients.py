"""Compare synthetic CPU/MPS controls; norms are not full gradient-vector parity."""
import argparse
import hashlib
import json
from pathlib import Path


def compare(cpu, mps):
    if len(cpu['steps']) != 3 or len(mps['steps']) != 3:
        raise ValueError('Expected all three optimization steps')
    differences=[]
    for a,b in zip(cpu['steps'],mps['steps']):
        if a['step'] != b['step'] or a['parameter_gradient_norms'].keys() != b['parameter_gradient_norms'].keys():
            raise ValueError('Control topology differs')
        values=[(a['loss'],b['loss']),
                (a['encoder_gradient_cpu_float64_norm'],b['encoder_gradient_cpu_float64_norm'])]
        values += [(value,b['parameter_gradient_norms'][key]) for key,value in a['parameter_gradient_norms'].items()]
        for x,y in values:
            import math
            if not math.isfinite(x) or not math.isfinite(y) or abs(x-y)>1e-6+1e-3*abs(x):
                raise ValueError(f'CPU/MPS control disagreement at step {a["step"]}: {x}, {y}')
        differences.append(max(abs(x-y) for x,y in values))
    for report in (cpu,mps):
        if not report['checked_parameter_max_abs_change']>0 or report['steps'][-1]['loss']>=report['steps'][0]['loss']:
            raise ValueError('Missing parameter update or loss reduction')
    return dict(status='passed_synthetic_loss_update_and_gradient_norm_control',
                max_absolute_difference_by_step=differences,rtol=.001,atol=.000001,
                limitation='Single synthetic example; parameter norms, not full gradient vectors; no semantic accuracy claim')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpu',type=Path,required=True)
    parser.add_argument('--mps',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    plans=[json.loads((p/'plan.json').read_text()) for p in (args.cpu,args.mps)]
    if plans[0].pop('device')!='cpu' or plans[1].pop('device')!='mps' or plans[0]!=plans[1]:
        raise ValueError('Mismatched experimental plans')
    report=compare(*(json.loads((p/'result.json').read_text()) for p in (args.cpu,args.mps)))
    report['inputs']={str(p/name):hashlib.sha256((p/name).read_bytes()).hexdigest()
                      for p in (args.cpu,args.mps) for name in ('plan.json','result.json')}
    report['implementation_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__),Path(__file__).with_name('probe_musicfm_gradients.py'))}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
