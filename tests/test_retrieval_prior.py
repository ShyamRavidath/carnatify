import pytest
from carnatify.ml.retrieval_prior import raga_prior_cost


def test_prior_is_bounded_and_does_not_filter_unknown_raga():
    p={'Bhairavi':.8,'Kambhoji':.2}
    assert raga_prior_cost(.3,'Bhairavi',p)==pytest.approx(.32)
    assert raga_prior_cost(.3,'Unknown',p)==pytest.approx(.4)
    assert raga_prior_cost(.3,'Unknown',{})==.3


def test_zero_weight_recovers_original_cost():
    assert raga_prior_cost(.25,'A',{'A':.1,'B':.9},0)==.25


def test_invalid_distribution_does_not_silently_change_rank():
    with pytest.raises(ValueError):raga_prior_cost(.3,'A',{'A':2.})
