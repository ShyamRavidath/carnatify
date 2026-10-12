"""labels_to_intervals must reproduce the hand-recovered manifest and refuse unreadable notes."""
import json
from pathlib import Path

import pytest

from scripts.labels_to_intervals import LabelError, build_resolver, convert, interpret_notes
from scripts.long_concert_score import validate_intervals

ROOT = Path(__file__).resolve().parent.parent
FROZEN = json.loads((ROOT / 'data/long_concerts/FROZEN_CONCERTS.json').read_text())
VOCAB = ['Śankarābharaṇaṁ', 'Tōḍi', 'Hindōḷaṁ', 'Ānandabhairavi', 'Varāḷi', 'Kalyāṇi',
         'Hamīr kaḷyaṇi', 'Dhēnukā', 'Kalānidhi']

# Concerts 1-3 as Deepti wrote them (mixed tabs and space runs), 2026-10-11.
ROWS = (
    "concert\tstart\traga\titem\tconfidence\tnotes\n"
    "long_concert_1  0:02    shankaraabharaNam   sarOja daLanEtri    high   at 12:35, thani avartanam starts, "
    "from then ignore the rest of the recording until 24:00. at 25:03, song ends, ignore rest of clip. \t\t\n"
    "long_concert_2  0:12    tODi    Era naapai  high    song ends at 7:02, from then on in nothing + alapana for second song \t\n"
    "long_concert_2\t15:14   hindOLam    saamagaana lOlanE   high    song ends at 28:38\t\t\n"
    "long_concert_2  29:15   dhEnukaa    teliyalEru raama    high    song gets aburptly cut off at the end of the clip -- the song isn't finished\t\n"
    "long_concert_3\t1:00    Anandabhairavi  pAhi shrI girirAjasutE  high    song ends 7:38; until next song is noise + alap as closer to song\t\n"
    "long_concert_3  19:15   varALi  mAmava mInAkSI rAjamAtangi  high    song ends 32:40; structure of song-noise-alaap-song is ubiquitous\t\n"
    "long_concert_3\t34:18   hamir kalyaNi   Sharade Karunanidhe high    song ends around 39:00, part of the ending 2-3 min of the song is muted, for some reason\t\n"
    "long_concert_3  39:39   kalAnidhi   cinna nADE nA ceyi baTTitivE    high    song ends at 42:33\t\n"
    "long_concert_3\t\t\t\t\n"
)

# (concert, start, end, raga, primary) from the hand-recovered manifest at source a0d137ea.
RECOVERED = [
    ('long_concert_1', 2, 755, 'Śankarābharaṇaṁ', True),
    ('long_concert_1', 1440, 1503, 'Śankarābharaṇaṁ', True),
    ('long_concert_2', 12, 422, 'Tōḍi', True),
    ('long_concert_2', 914, 1718, 'Hindōḷaṁ', True),
    ('long_concert_2', 1755, 1951.985, 'Dhēnukā', True),
    ('long_concert_3', 60, 458, 'Ānandabhairavi', True),
    ('long_concert_3', 1155, 1960, 'Varāḷi', True),
    ('long_concert_3', 2058, 2340, 'Hamīr kaḷyaṇi', False),
    ('long_concert_3', 2379, 2553, 'Kalānidhi', True),  # confidence was blank then, high now
]


def _convert(tmp_path, text):
    p = tmp_path / 'LABELS.tsv'
    p.write_text(text)
    return convert(p, FROZEN, build_resolver(VOCAB))


def test_reproduces_recovered_intervals(tmp_path):
    m = _convert(tmp_path, ROWS)
    validate_intervals(m, FROZEN)
    got = [(r['concert'], r['start_s'], round(r['end_s'], 3), r['raga'], r['primary']) for r in m['intervals']]
    assert got == RECOVERED
    assert {r['item_id'] for r in m['intervals'] if r['concert'] == 'long_concert_1'} == {'c1_1'}
    assert [(x['kind'], x['start_s'], x['end_s']) for x in m['exclusions']] == [
        ('tani', 755, 1440), ('after_song', 1503, 1605.753)]


def test_unscored_rows_are_not_intervals(tmp_path):
    m = _convert(tmp_path, "long_concert_4\t0:00\tragamalika\tviruttam\thigh\t\n"
                           "long_concert_4\t5:00\tKalyani\tnidhi\thigh\t\n")
    assert [r['start_s'] for r in m['intervals']] == [300]
    assert m['unscored'][0]['raga_raw'] == 'ragamalika'


def test_unparsed_note_time_is_an_error():
    with pytest.raises(LabelError, match='not covered'):
        interpret_notes('mic drops out at 3:10', 0, 600, 1)


def test_song_end_outside_row_is_an_error():
    with pytest.raises(LabelError, match='outside the row'):
        interpret_notes('song ends at 12:00', 0, 600, 1)


def test_ambiguous_loose_spelling_stays_raw():
    resolve = build_resolver(['Sāveri', 'Saveri'])
    assert resolve('saaveri')[1] == 'ambiguous'
