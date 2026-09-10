import numpy as np
import torch
from carnatify.ml.pitch_sequence import sequence_features,PitchTemporalConv


def test_ten_second_tonic_invariance_and_silence_timing():
    f=np.r_[np.full(400,220.),np.zeros(200),np.full(400,330.)]
    a=sequence_features(f,110,.01,10)
    b=sequence_features(f*1.37,110*1.37,.01,10)
    np.testing.assert_allclose(a,b,atol=1e-6)
    assert a.shape==(13,100)
    assert np.all(a[:,40:60]==0)
    assert np.all(a[-1,:40]==1)


def test_sequence_gradient_and_tiny_batch_learning():
    torch.set_num_threads(2);torch.manual_seed(42)
    a=sequence_features(np.full(1000,220.),110,.01,10)
    b=sequence_features(np.full(1000,330.),110,.01,10)
    x=torch.from_numpy(np.stack([a,b]));y=torch.tensor([0,1])
    model=PitchTemporalConv(2,width=8);optimizer=torch.optim.Adam(model.parameters(),lr=.01)
    losses=[]
    for _ in range(20):
        optimizer.zero_grad();loss=torch.nn.functional.cross_entropy(model(x),y)
        loss.backward()
        assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())
        optimizer.step();losses.append(float(loss.detach()))
    assert losses[-1]<losses[0]*.2
