"""Group-weighted temperature fitting and explicit selective predictions."""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import softmax,logsumexp


def group_weights(groups):
    _,inverse,count=np.unique(np.asarray(groups),return_inverse=True,return_counts=True)
    w=1/count[inverse]
    return w/w.sum()


def fit_temperature(probabilities,targets,groups):
    p=np.asarray(probabilities,dtype=float);y=np.asarray(targets,dtype=int)
    if p.ndim!=2 or len(p)!=len(y) or len(groups)!=len(y):
        raise ValueError('Calibration dimensions do not match')
    if not len(y) or not np.isfinite(p).all() or (p<0).any() or (p.sum(1)<=0).any():
        raise ValueError('Invalid calibration probabilities')
    if np.any((y<0)|(y>=p.shape[1])): raise ValueError('Invalid target index')
    logits=np.log(np.maximum(p,1e-30));w=group_weights(groups)
    def loss(log_t):
        z=logits/np.exp(log_t)
        return float(np.sum(w*(logsumexp(z,axis=1)-z[np.arange(len(y)),y])))
    result=minimize_scalar(loss,bounds=(-3,3),method='bounded')
    return dict(temperature=float(np.exp(result.x)),nll_before=loss(0),
                nll_after=float(result.fun),n_groups=len(set(groups)))


def temperature_scale(probabilities,temperature):
    if not np.isfinite(temperature) or temperature<=0:raise ValueError('Invalid temperature')
    return softmax(np.log(np.maximum(probabilities,1e-30))/temperature,axis=-1)


def selective_threshold(probabilities,targets,target_precision=.8,min_answers=30):
    """Choose highest coverage with an empirical precision target on calibration.

    This does not certify external precision or OOV rejection. The report keeps
    those limits explicit. Infeasible targets produce an always-abstain gate.
    """
    p=np.asarray(probabilities);y=np.asarray(targets)
    confidence=p.max(1);correct=p.argmax(1)==y
    feasible=[]
    for threshold in sorted(set(confidence)):
        mask=confidence>=threshold;n=int(mask.sum())
        if n>=min_answers and correct[mask].mean()>=target_precision:
            feasible.append((n,float(threshold),float(correct[mask].mean())))
    if not feasible:
        return dict(threshold=1.000001,coverage=0.,precision=None,answers=0,
                    status='target_infeasible_on_calibration')
    n,t,precision=max(feasible)
    return dict(threshold=t,coverage=n/len(y),precision=precision,answers=n,
                status='empirical_in_vocabulary_calibration_only')
