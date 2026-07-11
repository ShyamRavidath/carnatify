# %% [markdown]
# # Carnatify ASR sprint (Colab GPU)
#
# Goal: beat whisper large-v3-turbo CPU transcripts on the wild test clips.
# Tests 4 levers from HANDOFF_CLIP_ID.md §6.2 on the same clips:
#   A. whisper large-v3 (non-turbo), GPU
#   B. demucs vocal-stem isolation BEFORE whisper (untested, high hope)
#   C. VAD chunking (whisper's own condition_on_previous_text off + 30s chunks)
#   D. catalog-biased initial_prompt
#
# HOW TO RUN:
#   1. Runtime -> Change runtime type -> GPU (T4 fine).
#   2. Zip your test clips locally:  cd ~/sung_tests && zip clips.zip *.m4a
#   3. Run all cells; upload clips.zip when prompted.
#   4. Download the resulting transcripts_gpu.json and give it back to Claude.
#
# Output: transcripts_gpu.json with one entry per (clip, variant).
# Scoring happens back on the laptop against the catalog (no need here).

# %% Install (2-3 min)
!pip -q install -U openai-whisper demucs librosa soundfile

# %% Upload clips
from google.colab import files
import zipfile, io, os
os.makedirs('clips', exist_ok=True)
up = files.upload()  # upload clips.zip
zname = list(up.keys())[0]
with zipfile.ZipFile(io.BytesIO(up[zname])) as z:
    z.extractall('clips')
clip_files = sorted(f for f in os.listdir('clips')
                    if f.lower().endswith(('.m4a', '.wav', '.mp3', '.flac')))
print(len(clip_files), 'clips:', clip_files)

# %% Load audio (librosa handles m4a)
import librosa, numpy as np
audios = {}
for f in clip_files:
    y, _ = librosa.load(f'clips/{f}', sr=16000, mono=True)
    audios[f] = y.astype('float32')
    print(f, f'{len(y)/16000:.0f}s')

# %% Variant B prep: demucs vocal stems (GPU, ~30s/clip)
import torch, subprocess, soundfile as sf
os.makedirs('wav16', exist_ok=True)
for f in clip_files:
    sf.write(f'wav16/{os.path.splitext(f)[0]}.wav', audios[f], 16000)
!python -m demucs --two-stems=vocals -o stems wav16/*.wav
vocal_audios = {}
for f in clip_files:
    stem = f'stems/htdemucs/{os.path.splitext(f)[0]}/vocals.wav'
    if os.path.exists(stem):
        y, _ = librosa.load(stem, sr=16000, mono=True)
        vocal_audios[f] = y.astype('float32')
print('vocal stems:', len(vocal_audios))

# %% Transcribe all variants
import whisper, json, re, unicodedata

def fold(s):
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9 ]', '', t.lower())

model = whisper.load_model('large-v3')  # non-turbo, GPU
PROMPT = ('Carnatic music kriti in Telugu, Tamil, Sanskrit or Kannada. '
          'Composers: Tyagaraja, Dikshitar, Syama Sastri, Papanasam Sivan.')
LANGS = (None, 'ta', 'te', 'hi', 'kn')

def multi(audio, **kw):
    best = ''
    for lang in LANGS:
        try:
            r = model.transcribe(audio, language=lang, fp16=True, **kw)
            t = fold(r['text'])
            if len(t) > len(best):
                best = t
        except Exception as e:
            print('  err', lang, e)
    return best

out = {}
for f in clip_files:
    out[f] = {}
    out[f]['A_large_v3'] = multi(audios[f])
    if f in vocal_audios:
        out[f]['B_demucs_vocals'] = multi(vocal_audios[f])
    out[f]['C_nocond'] = multi(audios[f], condition_on_previous_text=False)
    out[f]['D_prompted'] = multi(audios[f], initial_prompt=PROMPT)
    if f in vocal_audios:
        out[f]['BD_vocals_prompted'] = multi(vocal_audios[f],
                                             initial_prompt=PROMPT)
    print(f)
    for k, v in out[f].items():
        print(f'  {k}: {v[:80]}')
    with open('transcripts_gpu.json', 'w') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

# %% Download result
files.download('transcripts_gpu.json')
