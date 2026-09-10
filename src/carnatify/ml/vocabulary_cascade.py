"""Fixed conditional combination of nested-vocabulary candidate models."""
import numpy as np


class VocabularyCascade:
    def __init__(self,narrow,broad):
        self.narrow=narrow;self.broad=broad
        self.classes_=np.asarray(broad.classes_)
        lookup={str(c):i for i,c in enumerate(self.classes_)}
        if len(lookup)!=len(self.classes_) or not set(map(str,narrow.classes_))<=set(lookup):
            raise ValueError('Expected unique, nested vocabularies')
        self.common_indices_=np.array([lookup[str(c)] for c in narrow.classes_])
        self.n_features_in_=narrow.n_features_in_
        if self.n_features_in_!=broad.n_features_in_:raise ValueError('Feature contracts differ')

    def predict_proba(self,X):
        broad=np.asarray(self.broad.predict_proba(X)).copy()
        narrow=np.asarray(self.narrow.predict_proba(X))
        common_mass=broad[:,self.common_indices_].sum(1,keepdims=True)
        # The broad model supplies mass for newly covered ragas. Conditional
        # common-raga discrimination comes from the narrow specialist. No label,
        # confidence-maximization rule, or fitted evaluation threshold enters.
        broad[:,self.common_indices_]=common_mass*narrow
        return broad

    def predict(self,X):
        return self.classes_[self.predict_proba(X).argmax(1)]
