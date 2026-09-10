"""Bounded query frontend shared by offline evaluation and concert inference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .pitch_profiles import HPSS_PARAMETERS, melodia_parameters, pitch_audio
from .cache_io import atomic_npz

VERSION = 'mixed_tonic_query_melodia_v1'
HOP_S = 128 / 44100


def extract_waveform(audio, sr=44100, profile='default'):
    """Estimate Sa on the original mix; extract melody from the chosen profile."""
    import essentia.standard as es
    parameters = melodia_parameters(profile, sr)
    tonic = float(es.TonicIndianArtMusic(sampleRate=sr)(audio))
    f0, _ = es.PredominantPitchMelodia(**parameters)(
        es.EqualLoudness(sampleRate=sr)(pitch_audio(audio, profile)))
    return f0, tonic


def query_contract(audio_sha256, start_s, duration_s, profile='default'):
    if (len(audio_sha256) != 64 or any(c not in '0123456789abcdef' for c in audio_sha256)
            or not np.isfinite(start_s) or start_s < 0
            or not np.isfinite(duration_s) or not 0 < duration_s <= 180):
        raise ValueError('Invalid bounded melody query')
    return dict(version=VERSION, audio_sha256=audio_sha256,
                start_s=float(start_s), duration_s=float(duration_s),
                melodia_parameters=melodia_parameters(profile), profile=profile,
                hpss_parameters=HPSS_PARAMETERS if profile == 'harmonic' else None)


def extract_query(path, audio_sha256, start_s, duration_s, cache_dir, profile='default'):
    """Caller supplies the verified full-file hash once per recording.

    Query boundaries and all frontend parameters are part of the cache key.
    A three-minute query never borrows a one-minute neighbor's tonic.
    """
    contract = query_contract(audio_sha256, start_s, duration_s, profile)
    key = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    target = Path(cache_dir) / f'{key}.npz'
    if target.exists():
        with np.load(target, allow_pickle=False) as z:
            meta = json.loads(str(z['meta']))
            if meta['contract'] != contract:
                raise ValueError('Melody query cache contract mismatch')
            f0 = z['f0']
        if f0.ndim != 1 or not np.isfinite(f0).all() or np.any(f0 < 0):
            raise ValueError('Invalid cached pitch contour')
        return f0, meta
    from .utils import load_audio_window
    audio, sr, diagnostics = load_audio_window(path, start_s, duration_s, 44100)
    failure = None
    tonic = None
    if len(audio) / sr < 10 or diagnostics['rms'] < 1e-5:
        f0 = np.zeros(0, dtype=np.float32)
    else:
        try:
            f0, tonic = extract_waveform(audio, sr, profile)
        except RuntimeError as exc:
            f0 = np.zeros(0, dtype=np.float32)
            failure = str(exc)
    f0 = f0[:int(np.ceil(len(audio) / sr / HOP_S))]
    if tonic is not None and (not np.isfinite(tonic) or tonic <= 0):
        tonic = None
    meta = dict(contract=contract, tonic_hz=tonic, audio=diagnostics,
                extraction_failure=failure, actual_duration_s=len(audio) / sr)
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_npz(target, f0=f0, meta=json.dumps(meta, allow_nan=False))
    return f0, meta


def composition_query(path,audio_sha256,start_s,context_f0,context_meta,cache_dir,*,duration_s=None):
    """Use an exact bounded song query; default remains <=60 seconds."""
    context=context_meta['contract'];profile=context['profile']
    if context!=query_contract(audio_sha256,start_s,context['duration_s'],profile):
        raise ValueError('Composition context contract mismatch')
    duration=min(60.,context['duration_s']) if duration_s is None else duration_s
    query_contract(audio_sha256,start_s,duration,profile)
    if duration==context['duration_s']:return context_f0,context_meta
    return extract_query(path,audio_sha256,start_s,duration,cache_dir,profile)
