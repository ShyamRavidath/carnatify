"""Freeze a new one-track-per-artist Saraga AV test before reading any audio.

Selection is deterministic SHA256 ordering within artist, restricted to exact
or explicitly resolved model vocabulary and a 2 GB compressed download budget.
This is a small known-raga test, not an open-set or natural-prevalence estimate.
"""
import argparse,json,sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from normalize_ragas import fold,resolve,build_fold_index
from scripts.raga_pipeline import sha,write_json
from scripts.merge_raga_training import artist_key,known_artist
from scripts.saraga_av_matching import mixture_lookup,match_mixture,recording_identity


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--remaining-artists',action='store_true',
                    help='Separate fixed test: exclude all previously evaluated artists; use broader vocabulary')
    args=ap.parse_args()
    base=ROOT/'data/overhaul/saraga_av'
    out=(base/'remaining_artists' if args.remaining_artists else base)/'evaluation_plan.json'
    if out.exists():raise ValueError('Evaluation plan is frozen; do not replace it after scoring')
    modelmeta=ROOT/('data/overhaul/broader/raga.json' if args.remaining_artists else 'data/overhaul/combined/raga_ridge.json')
    vocab=build_fold_index(json.loads(modelmeta.read_text())['classes'])
    index=json.loads((base/'audio_index.json').read_text())
    metadata_paths=[p for p in sorted((base/'metadata').rglob('*.json'))
                    if not p.name.startswith('.') and '__MACOSX' not in p.parts]
    mixtures,artist_aliases,join_evidence=mixture_lookup(index['rows'],metadata_paths)
    trained=json.loads((ROOT/'data/overhaul/combined/manifest.json').read_text())['rows']
    prior_plan=base/'evaluation_plan.json'
    if args.remaining_artists:
        trained+=json.loads((ROOT/'data/overhaul/broader/train/manifest.json').read_text())['rows']
        trained+=json.loads((ROOT/'data/architecture_audit/manifest.json').read_text())['rows']
    provenance={r['stem']:r for r in json.loads((ROOT/'data/qmax_audit/provenance.json').read_text())}
    def canonical_artist(artist):
        key=artist_key(artist)
        return artist_aliases.get(key,key)
    reserved={canonical_artist(artist) for r in trained if (artist:=known_artist(r,provenance))}
    if args.remaining_artists:
        reserved.update(canonical_artist(r['artist']) for r in json.loads(prior_plan.read_text())['rows'])
    max_bytes=250000000 if args.remaining_artists else 80000000
    grouped=defaultdict(list);excluded=[]
    for p in metadata_paths:
        md=json.loads(p.read_text());artist=p.parent.parent.name
        ragas=md.get('raaga',[]);raw=ragas[0]['name'] if len(ragas)==1 else None
        label=resolve(raw,vocab,list(vocab)) if raw else None
        audio=match_mixture(p,mixtures,artist_aliases)
        if canonical_artist(artist) in reserved or not label or audio is None or audio['compressed_size']>max_bytes:
            excluded.append(dict(metadata=str(p.relative_to(ROOT)),raga_raw=raw,
                                 reason='artist_overlap_or_unresolved_label_or_missing_or_large_audio'));continue
        track_id,selection_key=recording_identity(audio)
        row=dict(track=track_id,source_mbid=md['mbid'],artist=artist,group='artist:'+fold(artist),
            title=md['title'],raga_raw=raw,raga=label,metadata=str(p.relative_to(ROOT)),
            metadata_sha256=sha(p),archive_member=audio,
            selection_key=selection_key)
        grouped[artist].append(row)
    selected=[min(rows,key=lambda r:r['selection_key']) for _,rows in sorted(grouped.items())]
    total=sum(r['archive_member']['compressed_size'] for r in selected)
    if total>2000000000:raise ValueError(f'Frozen selection exceeds 2 GB budget: {total}')
    write_json(out,dict(schema=1,role='fresh_known_raga_test',rows=selected,excluded=excluded,
        requires_new_manual_labels=False,compressed_bytes=total,license='CC-BY-4.0',
        model_sha256=json.loads(modelmeta.read_text())['model_sha256'],
        resolver_sha256=sha(ROOT/'normalize_ragas.py'),
        archive_artist_join_evidence=join_evidence,
        prior_artist_plan_sha256=sha(prior_plan) if args.remaining_artists else None,
        maximum_member_compressed_bytes=max_bytes,
        selection='one SHA256-ranked eligible track per artist; no audio or predictions consulted',
        limitations='Known vocabulary and size-limited cohort; unknown historical artist provenance remains unresolved.'))
    print(f'Frozen {len(selected)} tracks, {len({r["raga"] for r in selected})} ragas; {total/1e9:.2f} GB compressed')


if __name__=='__main__':main()
