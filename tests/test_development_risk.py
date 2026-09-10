import numpy as np
from scripts.calibrate_development_risk import choose_threshold


def test_gate_rejects_all_when_calibration_evidence_is_insufficient():
    assert choose_threshold(np.array([.99]),np.array([True]))>1
    assert choose_threshold(np.arange(20)/20,np.zeros(20,dtype=bool))>1


def test_unknown_errors_count_against_threshold():
    confidence=np.r_[np.full(10,.9),np.full(10,.8)]
    correct=np.r_[np.ones(10,dtype=bool),np.zeros(10,dtype=bool)]
    assert choose_threshold(confidence,correct)==.9
