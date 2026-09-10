import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry_hygiene import nonmusical_registry_reason


def test_event_headers_only_rejected_without_musical_support():
    row = dict(id='comp00000', canonical='AIR Chennai', ragas=['9-9-2002'])
    assert nonmusical_registry_reason(row)
    assert not nonmusical_registry_reason(dict(row, ragas=['Unknown rare raga']))
    assert not nonmusical_registry_reason(dict(row, ragas=[]))
    assert not nonmusical_registry_reason(dict(row, ragas=['2002', 'Todi']))
    for support in ({'has_lyrics': True}, {'n_tracks': 1},
                    {'karnatik_pages': ['c1']}, {'composers': ['Tyagaraja']}):
        assert not nonmusical_registry_reason(dict(row, **support))


def test_target_loading_filters_without_changing_ids_or_source(tmp_path, monkeypatch):
    import identify_clip as module
    data = tmp_path / 'data'
    data.mkdir()
    with sqlite3.connect(data / 'lyrics.db') as con:
        con.execute('create table lyrics_catalog (title text, lyrics_original text)')
    path = data / 'composition_registry.json'
    rows = [dict(id='comp00000', canonical='AIR Chennai', aliases=[], ragas=['2002']),
            dict(id='comp00017', canonical='Ninne Bhajana', aliases=[], ragas=['Nata'])]
    path.write_text(json.dumps(rows))
    before = path.read_bytes()
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'REGISTRY', path)
    monkeypatch.setattr(module, 'KARNATIK', data / 'absent.json')
    monkeypatch.setattr(module, 'LINK_OVERRIDES', data / 'absent_links.json')
    entries, _ = module.load_targets()
    assert [r['id'] for r in entries] == ['comp00017']
    assert path.read_bytes() == before
