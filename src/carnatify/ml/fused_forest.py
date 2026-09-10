"""Reproducible v4-style RF baseline with shared feature contract."""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import BaseEstimator,ClassifierMixin


class FusedForest(ClassifierMixin,BaseEstimator):
    def __init__(self,n_estimators=800,hist_weight=.4,n_jobs=4):
        self.n_estimators=n_estimators;self.hist_weight=hist_weight;self.n_jobs=n_jobs

    def fit(self,X,y,sample_weight=None):
        self.hist_=RandomForestClassifier(n_estimators=self.n_estimators,max_features='sqrt',
                        random_state=42,n_jobs=self.n_jobs).fit(X[:,:480],y,sample_weight=sample_weight)
        self.tdms_=RandomForestClassifier(n_estimators=self.n_estimators,max_features='sqrt',
                        random_state=42,n_jobs=self.n_jobs).fit(X[:,480:],y,sample_weight=sample_weight)
        self.classes_=self.hist_.classes_;self.n_features_in_=5280
        return self

    def predict_proba(self,X):
        X=np.asarray(X)
        if X.ndim!=2 or X.shape[1]!=5280:raise ValueError('Expected legacy fused 5280 features')
        return self.hist_weight*self.hist_.predict_proba(X[:,:480])+(1-self.hist_weight)*self.tdms_.predict_proba(X[:,480:])

    def predict(self,X):return self.classes_[self.predict_proba(X).argmax(1)]
