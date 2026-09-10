"""Frozen AudioSet event classifier for automatic concert activity annotation.

AudioSet sigmoid scores are multi-label scores, not mutually exclusive musical
ground truth. Mixed speech/music and uncertain regions remain explicit.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np


def calibrated_event(event,calibration):
    """Apply a separately versioned activity gate without discarding raw scores."""
    result=dict(event,raw_state=event.get('raw_state',event['state']))
    threshold=calibration['ratio_threshold'];floor=calibration['min_percussion_score']
    if not 0<=threshold<=1 or not 0<=floor<=1:raise ValueError('Invalid activity calibration')
    if event['state'] in {'silence','speech','applause'}:return result
    percussion=event['percussion'];melodic=event['melodic']
    ratio=percussion/max(1e-9,percussion+melodic)
    result['percussion_evidence_ratio']=ratio
    result['state']=('percussion' if percussion>=floor and ratio>=threshold else
                     'music' if event['music']>=.35 else 'uncertain')
    return result


class AudioEventClassifier:
    def __init__(self,model_dir: str|Path,threads=4):
        import torch
        from transformers import ASTFeatureExtractor,ASTForAudioClassification
        self.torch=torch
        torch.set_num_threads(threads)
        self.extractor=ASTFeatureExtractor.from_pretrained(str(model_dir),local_files_only=True)
        self.model=ASTForAudioClassification.from_pretrained(str(model_dir),local_files_only=True,
                                                            use_safetensors=True).eval()
        self.labels={int(i):v for i,v in self.model.config.id2label.items()}

    def predict(self,audio,sr=16000):
        x=np.asarray(audio,dtype=np.float32)
        if x.ndim!=1 or not x.size or not np.isfinite(x).all() or sr!=16000:
            raise ValueError('Audio event model requires finite mono 16kHz input')
        if len(x)>160000:
            raise ValueError('Audio event window cannot exceed 10 seconds')
        inp=self.extractor(x,sampling_rate=sr,return_tensors='pt')
        with self.torch.inference_mode():
            scores=self.model(**inp).logits.sigmoid()[0].cpu().numpy()
        top=np.argsort(-scores)[:8]
        by_name={self.labels[i]:float(s) for i,s in enumerate(scores)}
        music=max(by_name.get(k,0) for k in ['Music','Singing','Musical instrument'])
        speech=max(by_name.get(k,0) for k in ['Speech','Conversation','Narration, monologue'])
        applause=max(by_name.get(k,0) for k in ['Applause','Clapping','Cheering'])
        percussion=max(by_name.get(k,0) for k in ['Percussion','Drum','Tabla'])
        melodic=max((value for name,value in by_name.items() if name!='Singing bowl' and
                     any(word in name.lower() for word in ['singing','violin','string','sitar','flute','piano','guitar','saxophone','clarinet'])),default=0.)
        # Deliberately permit mixed/unknown rather than forcing a single class.
        state=('applause' if applause>=.35 and applause>music else
               'speech' if speech>=.35 and speech>music else
               'percussion' if percussion>=.6 and melodic<.15 else
               'music' if music>=.35 else 'uncertain')
        return dict(state=state,music=music,speech=speech,applause=applause,
                    percussion=percussion,melodic=melodic,
                    top_events=[dict(event=self.labels[i],score=float(scores[i])) for i in top])
