"""Conservative admission checks for legacy composition metadata.

These checks do not validate work identity or manufacture raga labels.
Keep registry IDs stable: filter at consumption, never renumber the source.
"""
import re

_YEAR = re.compile(r'\b(?:19|20)\d{2}\b')


def nonmusical_registry_reason(row):
    """Reject unsupported event headers whose only raga fields contain years.

    Missing/unfamiliar raga names alone are not evidence of a bad composition.
    Any recording, lyric, or composer support conservatively retains the row.
    """
    supported = (row.get('n_tracks', 0) or row.get('has_lyrics')
                 or row.get('karnatik_pages') or row.get('composers'))
    ragas = row.get('ragas') or []
    if not supported and ragas and all(_YEAR.search(str(r)) for r in ragas):
        return 'unsupported_event_header_with_calendar_year_raga'
    return None
