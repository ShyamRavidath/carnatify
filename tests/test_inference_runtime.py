import numpy as np
from sklearn.ensemble import RandomForestClassifier
from carnatify.ml.inference_runtime import serial_forest_prediction
from carnatify.ml.fused_forest import FusedForest


def test_serial_prediction_preserves_fitted_probabilities():
    rng=np.random.default_rng(42);X=rng.normal(size=(20,4));y=np.arange(20)%2
    m=RandomForestClassifier(n_estimators=8,n_jobs=2,random_state=42).fit(X,y)
    expected=m.predict_proba(X)
    assert serial_forest_prediction(m) is m
    assert m.n_jobs==1
    np.testing.assert_allclose(m.predict_proba(X),expected)


def test_nested_forest_runtime_is_updated():
    model=FusedForest()
    model.hist_=RandomForestClassifier(n_jobs=4)
    model.tdms_=RandomForestClassifier(n_jobs=4)
    serial_forest_prediction(model)
    assert model.n_jobs==model.hist_.n_jobs==model.tdms_.n_jobs==1
