"""Conservative filename joins within the published Saraga AV archive.

These are archive artist spelling correspondences, never raga label aliases.
Each nontrivial correspondence must be corroborated by multiple exact folded
composition-directory names in this same release.
"""
from pathlib import Path
import hashlib
from normalize_ragas import fold

ARTIST_CORRESPONDENCES = {
    'Srividya Vadanamali': 'Srividya Vadnamali',
    'Vivek Mozhikkulam': 'Vivek Mozhikulam',
    'Hari Krishan': 'Hari Kishan',
    'Shraddha Ganesh': 'Shradda Ganesh',
}


def recording_identity(archive_member):
    # This release's top-level mbid is repeated across an artist's tracks
    # (232 metadata records, only 37 values). It is not a recording key.
    digest=hashlib.sha256(archive_member['path'].encode()).hexdigest()
    return 'saraga_av__'+digest[:24],digest


def mixture_lookup(index_rows, metadata_paths):
    lookup = {}
    audio_titles = {}
    metadata_titles = {}
    for path in metadata_paths:
        path = Path(path)
        metadata_titles.setdefault(path.parent.parent.name, set()).add(fold(path.parent.name))
    for row in index_rows:
        path = Path(row['path'])
        if not row['path'].endswith('.wav') or '.multitrack-' in row['path']:
            continue
        artist, title = path.parts[1:3]
        key = (fold(artist), fold(title))
        if key in lookup:
            raise ValueError('Ambiguous folded archive mixture identity')
        lookup[key] = row
        audio_titles.setdefault(artist, set()).add(fold(title))
    aliases = {}
    evidence = {}
    generic = {fold(t) for t in ['Thillana', 'Ragam Thanam Pallavi', 'Mangalam']}
    for source, target in ARTIST_CORRESPONDENCES.items():
        if source not in metadata_titles:
            continue
        shared = (metadata_titles[source] & audio_titles.get(target, set())) - generic
        if len(shared) < 2:
            raise ValueError('Uncorroborated artist filename correspondence')
        aliases[fold(source)] = fold(target)
        evidence[source] = dict(archive_artist=target, exact_shared_titles=sorted(shared))
    return lookup, aliases, evidence


def match_mixture(metadata_path, lookup, aliases):
    path = Path(metadata_path)
    artist = fold(path.parent.parent.name)
    return lookup.get((aliases.get(artist, artist), fold(path.parent.name)))
