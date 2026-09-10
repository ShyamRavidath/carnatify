"""Versioned, pickle-free reference catalog for candidate melody retrieval."""
import json
import numpy as np
from carnatify.ml.melody_retrieval import melody_sequence,subsequence_distance
from carnatify.ml.retrieval_prior import raga_prior_cost

CATALOG_VERSION='relative_24bin_halfsecond_oti_v1'


class CompositionCatalog:
    def __init__(self,path):
        with np.load(path,allow_pickle=False) as z:
            if str(z['version'])!=CATALOG_VERSION:raise ValueError('Unknown composition catalog version')
            self.frames=z['frames'];self.offsets=z['offsets'];self.metadata=json.loads(str(z['metadata']))
        if self.frames.ndim!=2 or self.frames.shape[1]!=24 or not np.isfinite(self.frames).all():
            raise ValueError('Invalid reference melody frames')
        if len(self.offsets)!=len(self.metadata)+1 or self.offsets[0]!=0 or self.offsets[-1]!=len(self.frames) or np.any(np.diff(self.offsets)<0):
            raise ValueError('Invalid reference offsets')

    def rank(self,frequencies,tonic,hop_s,limit=5,exclude_audio_hashes=(),*,raga_probabilities=None,raga_weight=.1):
        query=melody_sequence(frequencies,tonic,hop_s)
        if len(query)<8:return []
        excluded=set(exclude_audio_hashes);scores={}
        for i,meta in enumerate(self.metadata):
            if meta.get('audio_sha256') in excluded:continue
            a,b=self.offsets[i:i+2]
            d=subsequence_distance(query,self.frames[a:b],transposition_invariant=True)
            if not np.isfinite(d):continue
            cost=raga_prior_cost(d,meta['raga'],raga_probabilities or {},raga_weight)
            if meta['work_id'] not in scores or cost<scores[meta['work_id']]['ranking_cost']:
                scores[meta['work_id']]=dict(work_id=meta['work_id'],title=meta['title'],raga=meta['raga'],
                    reference_track=meta['track'],distance=d,ranking_cost=cost,status='unverified_candidate',
                    identity_evidence=meta.get('identity_evidence','unspecified'))
        return sorted(scores.values(),key=lambda r:(r['ranking_cost'],r['work_id']))[:limit]
