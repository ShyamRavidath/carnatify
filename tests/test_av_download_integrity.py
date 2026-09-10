import pytest
from scripts.evaluate_saraga_av import verify_download_receipts
from scripts.raga_pipeline import sha


def test_changed_audio_or_receipt_is_rejected(tmp_path):
    audio=tmp_path/'one.wav';audio.write_bytes(b'frozen audio fixture')
    rows=[dict(track='one',audio='one.wav')]
    receipt=dict(plan_sha256='plan',rows=[dict(track='one',audio_sha256=sha(audio))])
    verify_download_receipts(rows,receipt,'plan',tmp_path)
    with pytest.raises(ValueError,match='another selection'):
        verify_download_receipts(rows,receipt,'different-plan',tmp_path)
    audio.write_bytes(b'changed audio fixture')
    with pytest.raises(ValueError,match='Audio changed'):
        verify_download_receipts(rows,receipt,'plan',tmp_path)


def test_missing_and_duplicate_receipts_fail_closed():
    with pytest.raises(ValueError,match='Audio changed'):
        verify_download_receipts([dict(track='one',audio='unused')],dict(plan_sha256='plan',rows=[]),'plan')
    receipt=dict(plan_sha256='plan',rows=[dict(track='one'),dict(track='one')])
    with pytest.raises(ValueError,match='Duplicate'):
        verify_download_receipts([],receipt,'plan')
