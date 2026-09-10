"""Explicit section semantics shared by activity evaluation planners.

Tanam/thanam is melodic improvisation; it must not be confused with tani.
These mappings classify activity only, never named ragas or compositions.
"""
import numpy as np

PERCUSSION={'tani','tani_avartanam','tani_avartana','tani_avarthanam'}
MELODIC={'pallavi','anupallavi','anupallvi','charanam','charanams','vocal_alap',
         'violin_alap','nereval','viruttham','tanam','thanam','jatisvara','jati_svaram',
         'kalpana_svara','kalpana_svaram','kalpana_svaras','kalpana_svarams',
         'ragamalika_svaras','mukthayi_svara','mukthayi_svaram','chittai_svara',
         'chittai_svaram','chittai_svaras','chittai_svarams'}


def section_activity(kind):
    kind=kind.strip().lower().replace(' ','_').replace('-','_')
    if kind in PERCUSSION:return 'percussion'
    if kind in MELODIC or kind.startswith('charanam_') or kind.startswith('verse_'):
        return 'melodic_music'
    return None


def plan_activity_queries(corpus):
    rows=[];seen=set()
    for track in sorted(corpus,key=lambda r:r['track']):
        sections=track['sections']
        for index,section in enumerate(sections):
            a,b=section['start_s'],section['end_s'];truth=section_activity(section['kind'])
            if not np.isfinite(a) or not np.isfinite(b) or not 0<=a<b:
                raise ValueError('Invalid annotated section bounds')
            if truth is None or b-a<12:continue
            for fraction in (.2,.5,.8):
                start=(a+b)/2-5 if fraction==.5 else a+(b-a-10)*fraction
                if any(section_activity(other['kind']) not in (None,truth)
                       and max(start,other['start_s'])<min(start+10,other['end_s']) for other in sections):
                    raise ValueError('Conflicting activity annotations overlap a planned query')
                key=(track['track'],round(start,6))
                if key in seen:continue
                seen.add(key)
                rows.append(dict(track=track['track'],audio=track['audio'],section=section['kind'],
                                 section_id=f'{track["track"]}::{index}',start_s=start,truth=truth))
    return rows


def artist_class_weights(y,groups):
    """Equal class mass and equal artist mass within each class, using train rows only."""
    y=np.asarray(y);groups=np.asarray(groups)
    if len(y)!=len(groups) or not len(y):raise ValueError('Invalid activity weight inputs')
    weights=np.zeros(len(y),dtype=float)
    for label in np.unique(y):
        artists=np.unique(groups[y==label])
        for artist in artists:
            mask=(y==label)&(groups==artist)
            weights[mask]=1/(len(artists)*mask.sum())
    return weights/weights.mean()
