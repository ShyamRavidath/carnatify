"""Duration-weighted activity diagnostic on existing explicit intervals only.

Unlabeled time is excluded, not treated as music. This scores activity proposals,
not song boundaries or identities, and never supplies labels to inference.
"""
import argparse,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.raga_pipeline import sha,write_json


def score_segments(segments,truth):
    for rows in (segments,truth):
        previous=-math.inf
        for row in sorted(rows,key=lambda r:r['start_s']):
            a,b=row['start_s'],row['end_s']
            if not math.isfinite(a) or not math.isfinite(b) or a<0 or b<=a or a<previous:
                raise ValueError('Invalid or overlapping activity intervals')
            previous=b
    confusion={label:{p:0. for p in ('music','percussion','other','uncovered')}
               for label in ('music','percussion')}
    for target in truth:
        if target['truth'] not in confusion:raise ValueError('Invalid truth class')
        counts=confusion[target['truth']];covered=0.
        for segment in segments:
            overlap=max(0.,min(target['end_s'],segment['end_s'])-max(target['start_s'],segment['start_s']))
            kind=segment['kind']
            predicted='music' if kind=='melodic_music' else ('percussion' if kind=='percussion' else 'other')
            counts[predicted]+=overlap;covered+=overlap
        counts['uncovered']+=max(0.,target['end_s']-target['start_s']-covered)
    total=sum(sum(c.values()) for c in confusion.values())
    if not total:raise ValueError('No explicit activity truth')
    return dict(labeled_duration_s=total,confusion_duration_s=confusion,
        accuracy=sum(confusion[c][c] for c in confusion)/total,
        recall={c:confusion[c][c]/sum(counts.values()) if sum(counts.values()) else None
                for c,counts in confusion.items()})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reports',type=Path,nargs='+',required=True)
    ap.add_argument('--concert',required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    labels_path=ROOT/'data/architecture_audit/label_intervals.json'
    labels=json.loads(labels_path.read_text())
    if sha(ROOT/labels['source'])!=labels['source_sha256']:raise ValueError('Label source changed')
    truth=[dict(start_s=r['start_s'],end_s=r['end_s'],truth='music') for r in labels['intervals']
           if r['concert']==args.concert and r['primary'] and r['confidence']=='high']
    truth += [dict(start_s=r['start_s'],end_s=r['end_s'],truth='percussion') for r in labels['exclusions']
              if r['concert']==args.concert and r['kind']=='tani']
    rows=[];audio_hash=None
    for path in args.reports:
        report=json.loads(path.read_text());audio=Path(report['audio'])
        if audio.stem!=args.concert:raise ValueError('Concert/report mismatch')
        if not audio.is_absolute():audio=ROOT/audio
        digest=sha(audio)
        if digest!=report['audio_sha256'] or (audio_hash and digest!=audio_hash):
            raise ValueError('Audio mismatch')
        audio_hash=digest
        rows.append(dict(report=str(path),report_sha256=sha(path),**score_segments(report['segments'],truth)))
    write_json(args.out,dict(status='single-concert development diagnostic; not independent or identity accuracy',
        label_intervals_sha256=sha(labels_path),audio_sha256=audio_hash,rows=rows))
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
