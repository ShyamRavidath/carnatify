"""Fail closed when a candidate explicitly records evaluation contamination."""


def assert_unseen_tracks(bundle, rows):
    trained=set(bundle.get('training_track_ids', [])) | set(bundle.get('admitted_tracks', []))
    overlap=trained & {r['track'] for r in rows}
    if overlap:
        raise ValueError(f'Evaluation contains {len(overlap)} model training tracks; use held-out/OOF predictions')


def assert_unseen_audio(bundle, audio_sha256):
    """Exact bytes catch renamed copies; absence of receipts is not a pass."""
    if audio_sha256 in set(bundle.get('training_audio_sha256', [])):
        raise ValueError('Evaluation audio bytes occur in model training data')
    return bool(bundle.get('training_audio_sha256'))


def training_support(labels,tracks,groups):
    if not len(labels)==len(tracks)==len(groups):raise ValueError('Support metadata must align')
    support={}
    for label,track,group in zip(labels,tracks,groups):
        entry=support.setdefault(str(label),[set(),set()])
        entry[0].add(str(track));entry[1].add(str(group))
    return {label:dict(n_tracks=len(t),n_groups=len(g),limited_support=len(t)<5 or len(g)<3)
            for label,(t,g) in sorted(support.items())}
