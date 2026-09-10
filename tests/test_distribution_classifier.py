import numpy as np
import pytest
from carnatify.ml.distribution_classifier import DistributionSVC,DistributionKernelRidge,distribution_embedding


def features(n=12):
    X=np.zeros((n,4800));y=np.arange(n)%2
    for i in range(n):
        for j in range(3): X[i,j*1600+int(y[i])*700]=1
    return X,y


def test_distribution_geometry_and_scale():
    X,y=features()
    z=distribution_embedding(X)
    assert np.allclose(np.linalg.norm(z,axis=1),1)
    np.testing.assert_allclose(z,distribution_embedding(X*123))
    assert np.dot(z[0],z[1])==0


def test_svc_binary_multiclass_and_roundtrip(tmp_path):
    import joblib
    X,y=features()
    m=DistributionSVC().fit(X,y)
    np.testing.assert_array_equal(m.predict(X),y)
    assert m.predict_proba(X).shape==(12,2)
    assert np.allclose(m.predict_proba(X).sum(1),1)
    path=tmp_path/'model.joblib';joblib.dump(m,path)
    np.testing.assert_allclose(joblib.load(path).predict_proba(X),m.predict_proba(X))
    y=np.arange(12)%3
    X=np.zeros((12,4800))
    for i in range(12):X[i,y[i]*100]=1
    m.fit(X,y)
    assert m.predict_proba(X).shape==(12,3)
    np.testing.assert_array_equal(m.predict(X),y)


def test_invalid_distribution_rejected():
    with pytest.raises(ValueError):distribution_embedding(np.ones((5,10)))
    X,_=features();X[0,0]=np.nan
    with pytest.raises(ValueError):distribution_embedding(X)


def test_kernel_ridge_continuous_scores_and_fit():
    X,y=features();m=DistributionKernelRidge().fit(X,y)
    np.testing.assert_array_equal(m.predict(X),y)
    assert np.isfinite(m.predict_proba(X)).all()
    assert np.allclose(m.predict_proba(X).sum(1),1)


def test_calibration_reduces_overconfidence():
    from carnatify.ml.calibration import fit_temperature,temperature_scale,selective_threshold
    p=np.array([[.999,.001]]*50+[[.001,.999]]*50)
    y=np.array([0]*35+[1]*15+[1]*35+[0]*15)
    result=fit_temperature(p,y,np.arange(100)//10)
    assert result['temperature']>1 and result['nll_after']<result['nll_before']
    out=temperature_scale(p,result['temperature'])
    assert np.allclose(out.sum(1),1)
    gate=selective_threshold(out,y,target_precision=.9)
    assert gate['coverage']==0 and gate['threshold']>1
def test_kernel_rejects_invalid_configuration():
    from carnatify.ml.distribution_classifier import DistributionKernelRidge
    X=np.ones((4,4800));y=np.array(['A','A','B','B'])
    for kw in [{'alpha':0},{'gamma':float('nan')}]:
        with pytest.raises(ValueError):DistributionKernelRidge(**kw).fit(X,y)
    with pytest.raises(ValueError):DistributionKernelRidge().fit(X,y,sample_weight=[1,1,np.nan,1])
    with pytest.raises(ValueError):distribution_embedding(X,mode='typo')
