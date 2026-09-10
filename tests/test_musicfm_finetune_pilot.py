import numpy as np
import pytest
from scripts.finetune_musicfm_pilot import train_weights,contiguous_gradient


def test_fold_weights_use_training_counts_only():
    np.testing.assert_allclose(train_weights(np.array(['A','A','A','B']),['A','B']),[2/3,2])
    with pytest.raises(ValueError,match='no support'):train_weights(['A'],['A','B'])


def test_gradient_layout_hook_preserves_cpu_values():
    import torch
    torch.manual_seed(42)
    plain=torch.nn.Conv1d(4,4,1,bias=False)
    guarded=torch.nn.Conv1d(4,4,1,bias=False);guarded.load_state_dict(plain.state_dict())
    guarded.register_forward_hook(contiguous_gradient)
    x=torch.randn(2,4,7)
    plain(x).transpose(1,2).square().mean().backward()
    guarded(x).transpose(1,2).square().mean().backward()
    torch.testing.assert_close(plain.weight.grad,guarded.weight.grad)
