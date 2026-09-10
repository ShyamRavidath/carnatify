import numpy as np
import pytest
from carnatify.ml.vocabulary_cascade import VocabularyCascade


class Fixed:
    n_features_in_=2
    def __init__(self,classes,p):self.classes_=np.array(classes);self.p=np.array(p)
    def predict_proba(self,X):return np.tile(self.p,(len(X),1))


def test_common_probability_is_conditional_and_new_class_mass_is_preserved():
    model=VocabularyCascade(Fixed(['B','A'],[.25,.75]),Fixed(['A','B','C'],[.1,.3,.6]))
    p=model.predict_proba(np.ones((2,2)))
    np.testing.assert_allclose(p,[[.3,.1,.6]]*2)
    np.testing.assert_allclose(p.sum(1),1)


def test_vocabulary_mismatch_fails():
    with pytest.raises(ValueError):VocabularyCascade(Fixed(['X'],[1]),Fixed(['A','B'],[.5,.5]))
