"""Automate corpus/evaluation manifests from existing Saraga annotations.

No model predictions or new human labeling enter this manifest. Stable work IDs
support composition-rendition evaluation; metadata gaps remain explicit.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,sys,unicodedata

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import write_json,sha


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(s)).lower() if c.isalnum() and not unicodedata.combining(c))


def canonical_metadata_raga(tag,known):
    raw=known.get(fold(tag['name']));common=known.get(fold(tag.get('common_name','')))
    if raw and common and raw!=common:raise ValueError('Conflicting exact raga metadata names')
    return raw or common or tag['name']


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/annotated_corpus_v2.json')
    ap.add_argument('--training-run',type=Path,default=ROOT/'data/architecture_audit')
    args=ap.parse_args()
    import mirdata
    dataset=mirdata.initialize('saraga_carnatic',data_home=str(ROOT))
    training=json.loads((args.training_run/'manifest.json').read_text())
    train_groups={r['group'] for r in training['rows']}
    z=np.load(ROOT/'data/raga_coverage/matrix.npz')
    groups={str(t):str(g) for t,g in zip(z['g'],z['gc'])}
    train_groups.update(groups[r['track']] for r in training['rows'] if r['track'] in groups)
    known={fold(r['label']):r['label'] for r in training['rows']}
    rows=[];skipped=[]
    for tid in dataset.track_ids:
        t=dataset.track(tid);md=t.metadata or {}
        ragas=md.get('raaga') or []
        audio=Path(t.audio_path)
        if not audio.exists() or len(ragas)!=1:
            skipped.append(dict(track=tid,reason='missing_audio_or_not_single_raga'));continue
        raga=ragas[0]['name']
        canonical=canonical_metadata_raga(ragas[0],known)
        group=groups.get(tid,groups.get('saraga__'+tid))
        if group is None:
            # Resolve using another item in the same concert, before any score.
            concert='concert:'+audio.parent.parent.name
            group=concert
        work=md.get('work') or []
        pitch=getattr(t,'pitch_vocal_path',None) or getattr(t,'pitch_path',None)
        if not pitch or not Path(pitch).exists():
            choices=sorted(audio.parent.glob('*.pitch.txt'))
            pitch=str(choices[0]) if len(choices)==1 else None
        section_files=sorted(audio.parent.glob('*.sections-manual.txt'))
        sections=[]
        if len(section_files)==1:
            for line in section_files[0].read_text().splitlines():
                f=line.split('\t')
                if len(f)>=4:
                    a,duration=float(f[0]),float(f[2])
                    sections.append(dict(start_s=a,end_s=a+duration,kind=f[3]))
        tonic_path=next(iter(audio.parent.glob('*.ctonic.txt')),None)
        tonic=float(tonic_path.read_text().strip()) if tonic_path else None
        rows.append(dict(track=tid,audio=str(audio.relative_to(ROOT)),
            pitch=str(Path(pitch).relative_to(ROOT)) if pitch else None,
            tonic=tonic,raga_raw=raga,raga=canonical,
            raga_id=ragas[0].get('uuid'),raga_common_name=ragas[0].get('common_name'),
            in_training_vocabulary=fold(canonical) in known,group=group,
            source=audio.parent.parent.name,
            artists=[a['name'] for a in md.get('album_artists',[])],
            title=md.get('title'),work_id=work[0].get('mbid') if len(work)==1 else None,
            sections=sections,known_source_overlap=group in train_groups,
            annotation_source='Saraga distributed annotations',role='development_validation'))
    report=dict(schema=2,requires_new_manual_labels=False,rows=rows,skipped=skipped,
                training_manifest_sha256=sha(args.training_run/'manifest.json'),
                limitations='Known source/artist groups checked; unknown provenance is not proof of disjointness.')
    write_json(args.out,report)
    print(f'{len(rows)} annotated tracks, {sum(not r["known_source_overlap"] for r in rows)} without known training-group overlap; {sum(bool(r["sections"]) for r in rows)} with sections')


if __name__=='__main__':main()
