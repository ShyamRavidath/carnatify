"""Merge admitted archive and trusted CompMusic features with source unions."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from normalize_ragas import fold
from scripts.raga_pipeline import load_features,sha,write_json
from scripts.raga_audit_protocol import DSU
from carnatify.ml.melody_features import FEATURE_VERSION


def artist_key(name):
    k=fold(name)
    # Conservative grouping of possible spelling aliases: false joins reduce
    # independence/coverage, whereas treating possible copies as independent
    # would inflate CV. These are group unions, never musical label mappings.
    return {'kvnarayanaswamy':'kvnarayanaswami',
            'voletivenkateswarulu':'voletivenkateshwarlu'}.get(k,k)


def known_artist(row,provenance):
    artist=row.get('artist') or provenance.get(row['track'],{}).get('artist')
    return artist if artist and not artist.startswith('78 RPM') else None


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive-run',type=Path,default=ROOT/'data/architecture_audit')
    ap.add_argument('--compmusic-run',type=Path,default=ROOT/'data/overhaul/compmusic')
    ap.add_argument('--admission',type=Path,default=ROOT/'data/overhaul/taxonomy_admission.json')
    ap.add_argument('--out',type=Path,default=ROOT/'data/overhaul/combined')
    args=ap.parse_args()
    archive=args.archive_run.resolve();comp=args.compmusic_run.resolve();admission=args.admission.resolve()
    a=json.loads(admission.read_text())
    for p,d in a['inputs'].items():
        if sha(ROOT/p)!=d:raise ValueError('Stale taxonomy admission')
    allowed={r['track'] for r in a['rows'] if not r['status'].startswith('quarantine')}
    za=load_features(archive);zc=load_features(comp)
    ma=json.loads((archive/'manifest.json').read_text());mc=json.loads((comp/'manifest.json').read_text())
    rows=[dict(r,corpus='archive') for r in ma['rows'] if r['track'] in allowed]
    known={fold(r['label']):r['label'] for r in rows}
    rows.extend(dict(r,corpus='compmusic',label=known.get(fold(r['label']),r['label'])) for r in mc['rows'])
    prov={r['stem']:r for r in json.loads((ROOT/'data/qmax_audit/provenance.json').read_text())}
    dsu=DSU();first={}
    for r in rows:
        dsu.find(r['group'])
        artist=known_artist(r,prov)
        if artist:
            r['artist']=artist
            dsu.union(r['group'],'artist:'+artist_key(artist))
        digest=r['contour_sha256']
        if digest in first:dsu.union(r['group'],first[digest])
        first[digest]=r['group']
    members={}
    for r in rows:members.setdefault(dsu.find(r['group']),[]).append(r['group'])
    for r in rows:r['group']=min(members[dsu.find(r['group'])])
    by_track={r['track']:r for r in rows}
    mask=np.isin(za['track'],list(allowed))
    X=np.r_[za['X'][mask],zc['X']];legacy=np.r_[za['legacy'][mask],zc['legacy']]
    tracks=np.r_[za['track'][mask],zc['track']]
    labels=[by_track[str(t)]['label'] for t in tracks];groups=[by_track[str(t)]['group'] for t in tracks]
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    write_json(out/'manifest.json',dict(schema=1,role='development',corpus='admitted_archive_plus_compmusic',rows=rows,
        inputs={str(p.relative_to(ROOT)):sha(p) for p in [archive/'features.npz',comp/'features.npz',admission]},
        protocol=dict(group='source union known artist and identical contour',
                      limitation='Unknown artist provenance remains unresolved; front ends differ across corpora')))
    np.savez_compressed(out/'features.npz',X=X,legacy=legacy,y=np.array(labels),track=tracks,group=np.array(groups),
                        version=FEATURE_VERSION,manifest_sha256=sha(out/'manifest.json'))
    print(f'{len(rows)} tracks, {len(set(labels))} classes, {len(tracks)} windows, {len(set(groups))} groups')


if __name__=='__main__':main()
