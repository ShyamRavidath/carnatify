"""Regression tests for elapsed-time features, label ingestion and bounded DSP."""
import numpy as np
import pytest
import soundfile as sf
import torch

from carnatify.audio.feature_extractor import FeatureExtractor
from carnatify.audio.utils import load_audio_window, validate_audio
from carnatify.ml.melody_features import melody_features
from carnatify.ml.raga_model import RagaTDNN
from scripts.long_concert_labels import parse_row, parse_time


def test_sa_is_voiced_not_silence():
    fx = FeatureExtractor()
    hz = np.array([220., 0., 220., 220. * 2**(7/12)])
    cents = fx._normalize_pitch_contour(hz, 220.)
    pcd = fx._compute_pitch_class_distribution(cents, voiced_mask=hz > 0)
    assert pcd[0] == pytest.approx(2/3)
    assert pcd[7] == pytest.approx(1/3)


def test_tonic_invariance():
    rng = np.random.default_rng(42)
    f = 137 * 2**(rng.uniform(0, 24, 4000)/12)
    f[1000:1500] = 0
    expected = melody_features(f, 137, .01)
    for semitones in (-5.7, 3.2, 12):
        ratio = 2**(semitones/12)
        actual = melody_features(f*ratio, 137*ratio, .01)
        for a, b in zip(actual, expected):
            np.testing.assert_allclose(a, b, atol=1e-12)


def test_transition_counts_accumulate_and_do_not_bridge_silence():
    f = np.r_[np.full(90, 220.), 0., np.full(10, 220 * 2**(.7))]
    hist, _ = melody_features(f, 220, .01)
    bg = hist[120:264].reshape(12, 12)
    assert bg[0, 0] == pytest.approx(89/98)
    assert bg[0, 8] == 0
    assert bg[8, 8] == pytest.approx(9/98)


def test_elapsed_delays_do_not_join_separate_phrases():
    a = np.full(100, 220 * 2**(.02))
    b = np.full(100, 220 * 2**(.51))
    _, current = melody_features(np.r_[a, np.zeros(1000), b], 220, .01)
    _, baseline = melody_features(np.r_[a, np.zeros(1000), b], 220, .01, legacy=True)
    assert np.linalg.norm(current - baseline) > .001


@pytest.mark.parametrize('tonic,hop', [(np.nan,.01),(220,0),(220,np.inf),(-1,.01)])
def test_reject_invalid_coordinates(tonic, hop):
    with pytest.raises(ValueError):
        melody_features(np.ones(100), tonic, hop)


def test_antiphase_and_resampling_ten_seconds(tmp_path):
    sr = 48000
    y = .25*np.sin(2*np.pi*220*np.arange(sr*12)/sr)
    path = tmp_path/'stereo.wav'
    sf.write(path, np.c_[y,-y], sr, subtype='FLOAT')
    loaded, rate, diag = load_audio_window(path, 1, 10, 22050)
    assert len(loaded) == 220500 and rate == 22050
    assert diag['downmix'] == 'strongest_channel'
    assert np.sqrt(np.mean(loaded**2)) > .15
    assert not validate_audio(np.full(220500, np.nan), 22050)


@pytest.mark.parametrize('value', ['nan','inf','-1','1:60','1:99:00','1:-1'])
def test_invalid_time(value):
    assert parse_time(value) is None


def test_space_aligned_label_and_multiword_raga():
    row = parse_row('long_concert_3\t34:18   hamir kalyaNi   Sharade Karunanidhe high    ends 39:00\t\t')
    assert row['raga'] == 'hamir kalyaNi'
    assert row['item'] == 'Sharade Karunanidhe'
    assert row['confidence'] == 'high'
    assert parse_row('long_concert_4\t0:00\t\t\t\t')['raga'] == ''


def test_missing_confidence_never_becomes_high():
    row = parse_row('long_concert_3  39:39   kalAnidhi   cinna nADE    song ends at 42:33')
    assert row['raga'] == 'kalAnidhi' and row['confidence'] == ''


def test_concert_scorer_counts_failures_and_rejects_crossing_windows():
    from scripts.long_concert_score import score, validate_intervals
    labels = {'intervals':[
        dict(concert='a',item_id='1',start_s=10,end_s=80,raga='A',primary=True,confidence='high'),
        dict(concert='a',item_id='2',start_s=90,end_s=160,raga='B',primary=True,confidence='high'),
        dict(concert='a',item_id='3',start_s=170,end_s=240,raga='C',primary=True,confidence='high')]}
    validate_intervals(labels,{'concerts':[dict(file='a.mp3',duration_s=240)]})
    predictions=[('a',dict(start_s=10,end_s=70,probabilities={'A':.8,'B':.2})),
                 ('a',dict(start_s=90,end_s=150,status='abstained')),
                 ('a',dict(start_s=70,end_s=130,probabilities={'A':1}))]
    result=score(labels,predictions,{'A','B'})
    assert result['n_measured']==2 and result['n_missing']==1
    assert result['top1_all_measured']==.5
    assert result['vocabulary_coverage']==pytest.approx(2/3)
    assert len(result['rejected_windows'])==1


def test_concert_intervals_cannot_overlap_tani():
    from scripts.long_concert_score import validate_intervals
    with pytest.raises(ValueError,match='exclusion'):
        validate_intervals({'intervals':[dict(concert='a',start_s=0,end_s=100)],
            'exclusions':[dict(concert='a',start_s=50,end_s=70)]},
            {'concerts':[dict(file='a.mp3',duration_s=120)]})


def test_trainer_restores_best_checkpoint(tmp_path, monkeypatch):
    from carnatify.ml.raga_trainer import RagaTrainer
    from torch.utils.data import TensorDataset
    model=RagaTDNN(2,input_dim=12,hidden_dims=(4,4),dropout=0)
    trainer=RagaTrainer(model,epochs=3,checkpoint_dir=tmp_path,verbose=False)
    data=TensorDataset(torch.zeros(2,12),torch.tensor([0,1]))
    losses=iter([.1,.3,.6]); step=[0]
    def epoch(loader,train):
        if train:
            step[0]+=1
            with torch.no_grad():
                next(model.parameters()).fill_(step[0])
            return 1.,.5
        return next(losses),.5
    monkeypatch.setattr(trainer,'_run_epoch',epoch)
    result=trainer.train(data,data)
    assert result['best_epoch']==1
    assert torch.all(next(model.parameters())==1)


def test_synthetic_ten_second_contours_gradient_and_convergence():
    # Sanity only: these are synthetic modal patterns, not a raga benchmark.
    torch.manual_seed(42)
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        X, y = [], []
        for label, cents in enumerate(([0,200,400,700,900],[0,100,500,800,1100])):
            contour = 137*2**(np.repeat(cents,200)/1200)
            features, _ = melody_features(contour,137,.01)
            for _ in range(8):
                X.append(features[:120]); y.append(label)
        X = torch.tensor(np.array(X),dtype=torch.float32)
        y = torch.tensor(y)
        model = RagaTDNN(2,input_dim=120,hidden_dims=(32,16),dropout=0)
        opt = torch.optim.Adam(model.parameters(),lr=.03)
        criterion = torch.nn.CrossEntropyLoss()
        initial = criterion(model(X),y).item()
        for step in range(40):
            opt.zero_grad(); loss = criterion(model(X),y); loss.backward()
            assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
            opt.step()
        assert loss.item() < initial*.2
        assert (model(X).argmax(1)==y).float().mean() == 1
    finally:
        torch.set_num_threads(old_threads)
def test_legacy_fused_contract():
    from carnatify.ml.melody_features import feature_vector,melody_features
    f=np.repeat(220*2**(np.array([0,2,4,7,9,7,4,2])/12),500)
    parts=melody_features(f,220,.01,legacy=True)
    np.testing.assert_allclose(feature_vector(f,220,.01,'legacy_fused'),np.r_[parts[0],parts[1]])
