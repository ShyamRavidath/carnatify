import copy
import pytest
from scripts.compare_musicfm_gradients import compare


def control():
    return dict(checked_parameter_max_abs_change=.001,steps=[dict(step=i,loss=2/(i+1),
        encoder_gradient_cpu_float64_norm=.01,parameter_gradient_norms={'norm.weight':.001,'norm.bias':.009})
        for i in range(3)])


def test_matching_synthetic_controls():
    assert compare(control(),control())['status'].startswith('passed_')


@pytest.mark.parametrize('value',[26.45,float('nan'),float('inf')])
def test_rejects_wrong_affine_gradient_even_when_loss_decreases(value):
    gpu=copy.deepcopy(control());gpu['steps'][2]['parameter_gradient_norms']['norm.bias']=value
    with pytest.raises(ValueError,match='disagreement'):compare(control(),gpu)


def test_rejects_absent_encoder_update():
    gpu=control();gpu['checked_parameter_max_abs_change']=0
    with pytest.raises(ValueError,match='update'):compare(control(),gpu)
