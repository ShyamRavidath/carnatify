"""Distribution-aware raga classifier with an explicit shared transform.

Square-root probability embeddings use Hellinger geometry instead of treating
each sparse histogram bin as an unrelated tree feature. Scores are explicitly
uncalibrated until a source-disjoint calibration stage supplies a temperature.
"""
from __future__ import annotations

import numpy as np
from scipy.special import softmax
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.svm import SVC
from sklearn.metrics.pairwise import rbf_kernel
from scipy.linalg import solve


def distribution_embedding(X, mode='tdms'):
    if mode not in {'tdms','fused','multiscale','spd'}:raise ValueError('Unknown embedding mode')
    X = np.asarray(X,dtype=np.float64)
    if X.ndim != 2 or not np.isfinite(X).all() or np.any(X < -1e-12):
        raise ValueError('Expected a finite, nonnegative feature matrix')
    if mode=='spd':
        if X.shape[1]!=34560:raise ValueError('SPD features require 34560 bins')
        tensor=X.reshape(len(X),288,120)
        mass=tensor.sum(axis=-1,keepdims=True)
        out=np.sqrt(np.maximum(tensor,0)/np.maximum(mass,1e-20)).reshape(len(X),-1)
        return out/np.maximum(np.linalg.norm(out,axis=1,keepdims=True),1e-20)
    if mode=='multiscale':
        if X.shape[1]!=9600:raise ValueError('Six-scale features require 9600 bins')
        blocks=[X[:,i*1600:(i+1)*1600] for i in range(6)]
    elif X.shape[1] == 5280:
        blocks = ([X[:,:120],X[:,120:264],X[:,264:480]] if mode=='fused' else [])
        blocks += [X[:,480+i*1600:480+(i+1)*1600] for i in range(3)]
    elif X.shape[1] == 4800:
        if mode != 'tdms':
            raise ValueError('Histogram features missing')
        blocks = [X[:,i*1600:(i+1)*1600] for i in range(3)]
    else:
        raise ValueError('Unknown feature layout')
    parts=[]
    for b in blocks:
        mass=b.sum(axis=1,keepdims=True)
        parts.append(np.sqrt(np.maximum(b,0)/np.maximum(mass,1e-20)))
    out=np.concatenate(parts,axis=1)
    return out/np.maximum(np.linalg.norm(out,axis=1,keepdims=True),1e-20)


class DistributionSVC(ClassifierMixin,BaseEstimator):
    def __init__(self,C=10.0,gamma=2.0,mode='tdms',class_weight='balanced',temperature=1.0):
        self.C=C; self.gamma=gamma; self.mode=mode
        self.class_weight=class_weight; self.temperature=temperature

    def fit(self,X,y,sample_weight=None):
        self.model_=SVC(C=self.C,gamma=self.gamma,kernel='rbf',
                        class_weight=self.class_weight,decision_function_shape='ovr',
                        break_ties=True,cache_size=512,random_state=42)
        self.model_.fit(distribution_embedding(X,self.mode),y,sample_weight=sample_weight)
        self.classes_=self.model_.classes_
        self.n_features_in_=np.asarray(X).shape[1]
        return self

    def decision_function(self,X):
        scores=self.model_.decision_function(distribution_embedding(X,self.mode))
        if scores.ndim==1:
            scores=np.c_[-scores,scores]
        return scores

    def predict_proba(self,X):
        if not np.isfinite(self.temperature) or self.temperature<=0:
            raise ValueError('Temperature must be positive')
        return softmax(self.decision_function(X)/self.temperature,axis=1)

    def predict(self,X):
        return self.classes_[self.decision_function(X).argmax(axis=1)]


class DistributionKernelRidge(ClassifierMixin,BaseEstimator):
    """Multi-output RBF kernel ridge with class-balanced target regression.

    Unlike SVC's OVR vote counts, continuous class scores retain distance
    information for aggregation and calibration. One kernel is shared by all
    classes. Regularization is fixed in the experiment specification.
    """
    def __init__(self,alpha=.1,gamma=2.0,mode='tdms',temperature=1.0):
        self.alpha=alpha;self.gamma=gamma;self.mode=mode;self.temperature=temperature

    def fit(self,X,y,sample_weight=None):
        if not np.isfinite(self.alpha) or self.alpha<=0 or not np.isfinite(self.gamma) or self.gamma<=0:
            raise ValueError('Kernel regularization and gamma must be positive')
        self.classes_,yi=np.unique(y,return_inverse=True)
        self.reference_=distribution_embedding(X,self.mode)
        n=len(yi)
        if n==0 or len(self.reference_)!=n or np.asarray(y).ndim!=1:
            raise ValueError('Training examples and labels must align')
        weights=np.ones(n) if sample_weight is None else np.asarray(sample_weight,dtype=float)
        if weights.shape!=(n,) or not np.isfinite(weights).all() or np.any(weights<=0):
            raise ValueError('Weights must be finite, positive and aligned')
        counts=np.bincount(yi,weights=weights)
        weights=weights/counts[yi];weights/=weights.mean()
        K=rbf_kernel(self.reference_,gamma=self.gamma)
        K.flat[::n+1]+=self.alpha/weights
        Y=np.eye(len(self.classes_))[yi]
        self.dual_=solve(K,Y,assume_a='pos')
        self.n_features_in_=np.asarray(X).shape[1]
        return self

    def decision_function(self,X):
        return rbf_kernel(distribution_embedding(X,self.mode),self.reference_,gamma=self.gamma)@self.dual_

    def predict_proba(self,X):
        if not np.isfinite(self.temperature) or self.temperature<=0:
            raise ValueError('Temperature must be positive')
        return softmax(self.decision_function(X)/self.temperature,axis=1)

    def predict(self,X):
        return self.classes_[self.decision_function(X).argmax(1)]
