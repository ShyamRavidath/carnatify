from scripts.evaluate_sung_asr_titles import usable_text


def test_loop_and_missing_diagnostics_do_not_supply_title_evidence():
    h=dict(segments=[dict(text='fluent repeated text',avg_logprob=-.1,no_speech_prob=0.,compression_ratio=10.),
                     dict(text='missing diagnostics'),
                     dict(text='...',avg_logprob=-.1,no_speech_prob=0.,compression_ratio=1.)])
    assert usable_text(h)==''


def test_native_script_survives_matching_view():
    h=dict(segments=[dict(text='निन्ने भजन',avg_logprob=-.5,no_speech_prob=.1,compression_ratio=1.)])
    text=usable_text(h)
    assert 'ninne' in text and 'bajan' in text
    assert h['segments'][0]['text']=='निन्ने भजन'
