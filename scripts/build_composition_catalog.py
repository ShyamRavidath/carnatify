"""Build clean work-ID references from existing Saraga annotations, not registry guesses."""
import argparse,hashlib,json,sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from scripts.raga_pipeline import sha,write_json
from carnatify.ml.melody_retrieval import melody_sequence
from carnatify.ml.composition_catalog import CATALOG_VERSION
from normalize_ragas import fold
from scripts.merge_raga_training import known_artist


def specific_title(title):
    key=fold(title or '')
    generic={'alapana','tanam','thaanam','thani','tani','thillana','tillana','javali','mangalam',
             'slokam','viruttam','ragam','pallavi','varnam','unknown'}
    return bool(key) and key not in generic and not any(x in key for x in ['alapana','ragamtanampallavi','rtp'])


def reference_work_id(title,raga,known_works):
    key=(fold(title),fold(raga));matches=known_works.get(key,set())
    if len(matches)==1:return next(iter(matches))
    # Local provisional identity, never presented as an authoritative work ID.
    return 'weak-title:'+hashlib.sha256('|'.join(key).encode()).hexdigest()[:24]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--corpus',type=Path,default=ROOT/'data/overhaul/annotated_corpus.json')
    ap.add_argument('--archive-run',type=Path,help='Optional weak archival reference expansion')
    ap.add_argument('--admission',type=Path,help='Required with --archive-run; strict-tag entries only')
    args=ap.parse_args()
    if bool(args.archive_run)!=bool(args.admission):ap.error('--archive-run and --admission must be supplied together')
    corpus=args.corpus;rows=json.loads(corpus.read_text())['rows']
    frames=[];offsets=[0];metadata=[]
    for row in rows:
        if not row['work_id'] or not row['pitch'] or not row['tonic']:continue
        d=np.loadtxt(ROOT/row['pitch']);hop=float(np.median(np.diff(d[:,0])))
        seq=melody_sequence(d[:,1],row['tonic'],hop)
        if len(seq)<8:continue
        frames.append(seq);offsets.append(offsets[-1]+len(seq))
        metadata.append(dict(track=row['track'],work_id=row['work_id'],title=row['title'],raga=row['raga'],
            artists=row['artists'],source=row['source'],audio_sha256=sha(ROOT/row['audio']),
            pitch_sha256=sha(ROOT/row['pitch']),identity_evidence='distributed_work_annotation'))
    archive_inputs={};n_archive=0
    if args.archive_run:
        mp=args.archive_run/'manifest.json';admission=json.loads(args.admission.read_text())
        for p,digest in admission['inputs'].items():
            if sha(ROOT/p)!=digest:raise ValueError('Stale archive title admission')
        by_track={r['track']:r for r in json.loads(mp.read_text())['rows']}
        provenance={r['stem']:r for r in json.loads((ROOT/'data/qmax_audit/provenance.json').read_text())}
        known_works=defaultdict(set)
        for r in rows:
            if r['work_id'] and specific_title(r['title']):known_works[(fold(r['title']),fold(r['raga']))].add(r['work_id'])
        for admitted in admission['rows']:
            if admitted['status']!='strict_tag_consistent' or not specific_title(admitted['title']):continue
            row=by_track[admitted['track']];pitch=ROOT/row['contour']
            if sha(pitch)!=row['contour_sha256']:raise ValueError('Changed archive contour')
            seq=melody_sequence(np.load(pitch),row['tonic'],row['hop_s'])
            if len(seq)<8:continue
            audio=ROOT/row['audio'];artist=known_artist(row,provenance)
            frames.append(seq);offsets.append(offsets[-1]+len(seq));n_archive+=1
            metadata.append(dict(track=row['track'],title=admitted['title'],raga=row['label'],
                work_id=reference_work_id(admitted['title'],row['label'],known_works),
                artists=[artist] if artist else [],source=row['source'],group=row['group'],
                audio_sha256=sha(audio) if audio.exists() else None,pitch_sha256=sha(pitch),
                identity_evidence='weak_archive_title_metadata',source_urls=admitted['source_urls']))
        archive_inputs={str(mp):sha(mp),str(args.admission):sha(args.admission)}
    if not frames:raise ValueError('No usable composition references')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(args.out,version=CATALOG_VERSION,frames=np.concatenate(frames),offsets=np.array(offsets),
                        metadata=json.dumps(metadata,ensure_ascii=False))
    write_json(args.out.with_suffix('.json'),dict(version=CATALOG_VERSION,catalog_sha256=sha(args.out),
        corpus_sha256=sha(corpus),n_tracks=len(metadata),n_works=len({r['work_id'] for r in metadata}),
        n_weak_archive_references=n_archive,archive_inputs=archive_inputs,
        status='candidate retrieval only; no production acceptance threshold',
        source='Saraga distributed annotations; optional weak archival titles; retain original attribution/terms'))
    print(f'{len(metadata)} reference performances indexed')


if __name__=='__main__':main()
