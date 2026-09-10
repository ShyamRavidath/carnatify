"""Explicit, versioned Melodia extraction profiles for paired ablations."""

PROFILES = {
    'default': {},
    # Existing root clip configuration; not inferred from evaluation labels.
    'legacy_vocal': {'minFrequency': 90, 'maxFrequency': 900, 'voicingTolerance': .6},
    'harmonic': {},
}

HPSS_PARAMETERS=dict(kernel_size=31,power=2.,margin=2.,n_fft=2048,hop_length=512)


def pitch_audio(audio,profile='default'):
    if profile not in PROFILES:raise ValueError('Unknown pitch audio profile')
    if profile=='harmonic':
        import librosa
        return librosa.effects.harmonic(audio,**HPSS_PARAMETERS)
    return audio


def melodia_parameters(profile='default', sample_rate=44100):
    if profile not in PROFILES:
        raise ValueError(f'Unknown melody extraction profile: {profile}')
    if sample_rate != 44100:
        raise ValueError('These versioned profiles require 44100 Hz audio')
    return dict(sampleRate=sample_rate, frameSize=2048, hopSize=128, **PROFILES[profile])


def cache_suffix(profile='default',window_s=60):
    if profile not in PROFILES:
        raise ValueError(f'Unknown melody extraction profile: {profile}')
    if window_s not in {60,180}:
        raise ValueError('Supported fixed windows are 60 and 180 seconds')
    return f'center{window_s}_v1' if profile == 'default' else f'center{window_s}_{profile}_v1'
