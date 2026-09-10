"""Bounded offline sung-ASR hypotheses; never semantic ground truth."""
from pathlib import Path
import numpy as np
from .demucs_frontend import digest

CHECKPOINT_SHA256='aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a'
VERSION='whisper_turbo_cpu_greedy_unprompted_v1'
DECODE=dict(language=None,task='transcribe',temperature=0.,beam_size=1,fp16=False,
            condition_on_previous_text=False,initial_prompt=None,verbose=None,
            compression_ratio_threshold=2.4,logprob_threshold=-1.,no_speech_threshold=.6)


class SungASR:
    def __init__(self,checkpoint):
        if digest(checkpoint)!=CHECKPOINT_SHA256:raise ValueError('ASR checkpoint checksum mismatch')
        import whisper
        # An explicit local path prevents downloader fallback. The installed
        # upstream loader uses weights_only=True with this PyTorch version.
        self.model=whisper.load_model(str(Path(checkpoint)),device='cpu').eval()

    def transcribe(self,audio,sr=16000,*,language=None):
        if language not in (None,'ta','te','hi'):raise ValueError('Unsupported fixed ASR language lane')
        y=np.asarray(audio,dtype=np.float32)
        if y.ndim!=1 or not np.isfinite(y).all() or sr!=16000 or not 0<len(y)<=180*sr:
            raise ValueError('Expected bounded finite 16 kHz audio')
        if np.sqrt(np.mean(y**2))<1e-5:return dict(text='',segments=[],language=None,status='silence')
        result=self.model.transcribe(y,**{**DECODE,'language':language})
        text=(result.get('text') or '').strip()
        segments=[{k:s.get(k) for k in ('start','end','text','avg_logprob','no_speech_prob','compression_ratio')}
                  for s in result.get('segments',[])]
        return dict(text=text,segments=segments,language=result.get('language'),
                    status='unverified_hypothesis' if text else 'empty')
