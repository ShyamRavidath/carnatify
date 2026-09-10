"""Extract trusted distributed CompMusic pitch, excluding Saraga artists.

Raw CompMusic audio is not available locally: the reference front end is
explicitly different from live Melodia. No inferred labels are manufactured.
"""
from __future__ import annotations
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import mirdata
import numpy as np
from normalize_ragas import fold
from carnatify.ml.melody_features import melody_features,FEATURE_VERSION
from scripts.raga_pipeline import sha,write_json


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/compmusic')
    ap.add_argument('--reserved-corpus',type=Path,default=ROOT/'data/overhaul/annotated_corpus.json')
    args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    corpus=args.reserved_corpus
    reserved={fold(a) for r in json.loads(corpus.read_text())['rows'] for a in r['artists']}
    dataset=mirdata.initialize('compmusic_raga',data_home=str(ROOT))
    X=[];legacy=[];ys=[];tracks=[];groups=[];rows=[];skipped=[]
    start=time.monotonic()
    for t in dataset.load_tracks().values():
        if t.tradition!='carnatic':continue
        if fold(t.artist) in reserved:
            skipped.append(dict(track=t.track_id,reason='reserved_evaluation_artist'));continue
        if not t.tonic or t.tonic<=0 or not t.raga:
            skipped.append(dict(track=t.track_id,reason='missing_tonic_or_raga'));continue
        pitch=t.pitch
        if pitch is None:continue
        f=pitch.frequencies;hop=float(np.median(np.diff(pitch.times)))
        width=round(60/hop);tid='compmusic__'+t.track_id;group='artist:'+fold(t.artist)
        usable=0
        for a in sorted({round(max(0,len(f)-width)*q) for q in [.2,.5,.8]}):
            clip=f[a:a+width]
            if np.sum(np.isfinite(clip)&(clip>0))*hop<10:continue
            modern=melody_features(clip,t.tonic,hop)
            old=melody_features(clip,t.tonic,hop,legacy=True)
            if modern is None or old is None:continue
            X.append(np.r_[modern[0],modern[1]]);legacy.append(old[1]);ys.append(t.raga)
            tracks.append(tid);groups.append(group);usable+=1
        if usable:
            rows.append(dict(track=tid,label=t.raga,group=group,artist=t.artist,
                tonic=float(t.tonic),hop_s=hop,contour=str(Path(t.pitch_path).relative_to(ROOT)),
                contour_sha256=sha(t.pitch_path),frontend='CompMusic distributed pitch',windows=usable))
        if len(rows)%25==0:print(f'{len(rows)} admitted tracks; {time.monotonic()-start:.1f}s',flush=True)
    write_json(out/'manifest.json',dict(schema=1,role='development',corpus='compmusic_pitch',rows=rows,
        skipped=skipped,reserved_corpus_sha256=sha(corpus),
        protocol=dict(window_s=60,offsets=[.2,.5,.8],group='exact normalized artist',
                      limitation='reference pitch, not raw-audio extraction; unknown aliases may remain')))
    np.savez_compressed(out/'features.npz',X=np.array(X),legacy=np.array(legacy),y=np.array(ys),
        track=np.array(tracks),group=np.array(groups),version=FEATURE_VERSION,
        manifest_sha256=sha(out/'manifest.json'))
    print(f'{len(rows)} tracks, {len(set(ys))} classes, {len(X)} windows; {len(skipped)} excluded')


if __name__=='__main__':main()
