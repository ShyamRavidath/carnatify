# %% [markdown]
# # Carnatify ASR sprint 2: Indic models (Colab GPU)
#
# Goal: crack the 2 ASR-dead clips (Bhuvini Dasudane, Tulasi Bilva) and
# beat turbo elsewhere. Tests Indic-finetuned models that know Carnatic
# languages better than stock whisper:
#   A. vasista22/whisper-telugu-large-v2  (Telugu finetune)
#   B. vasista22/whisper-tamil-large-v2   (Tamil finetune)
#   C. ai4bharat/indicwav2vec (via transformers) — skipped if load fails
#   D. large-v3 (non-turbo) on DEMUCS STEMS — the proven Tulasi cracker,
#      re-run here so all winners land in one json
#
# HOW TO RUN (same drill as last time):
#   1. Runtime -> GPU (T4 fine).
#   2. Upload clips.zip (same one) when prompted.
#   3. Send back transcripts_indic.json.
#
# Each variant runs on BOTH original audio and demucs vocal stem.

# %% Install (~3 min)
!pip -q install -U transformers accelerate openai-whisper demucs librosa soundfile

# %% Upload + load clips
from google.colab import files
import zipfile, io, os
os.makedirs('clips', exist_ok=True)
up = files.upload()
with zipfile.ZipFile(io.BytesIO(up[list(up.keys())[0]])) as z:
    z.extractall('clips')
clip_files = sorted(f for f in os.listdir('clips')
                    if f.lower().endswith(('.m4a', '.wav', '.mp3', '.flac')))
print(len(clip_files), 'clips')

import librosa, numpy as np
audios = {f: librosa.load(f'clips/{f}', sr=16000, mono=True)[0].astype('float32')
          for f in clip_files}

# %% Demucs vocal stems
import torch, soundfile as sf
os.makedirs('wav', exist_ok=True)
for f in clip_files:
    sf.write(f'wav/{os.path.splitext(f)[0]}.wav', audios[f], 16000)
!python -m demucs --two-stems=vocals -o stems wav/*.wav
stems = {}
for f in clip_files:
    p = f'stems/htdemucs/{os.path.splitext(f)[0]}/vocals.wav'
    if os.path.exists(p):
        stems[f] = librosa.load(p, sr=16000, mono=True)[0].astype('float32')
print('stems:', len(stems))

# %% Helpers
import json, re, unicodedata
def fold(s):
    d = unicodedata.normalize('NFKD', s or '')
    t = ''.join(c for c in d if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9 ]', '', t.lower())

out = {}
def record(f, tag, text):
    out.setdefault(f, {})[tag] = text
    with open('transcripts_indic.json', 'w') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f'  {tag}: {text[:80]}')

# %% A+B: Indic whisper finetunes (transformers pipeline, transliterate via fold)
from transformers import pipeline
for tag, model_id, lang in (('te_ft', 'vasista22/whisper-telugu-large-v2', 'te'),
                            ('ta_ft', 'vasista22/whisper-tamil-large-v2', 'ta')):
    try:
        pipe = pipeline('automatic-speech-recognition', model=model_id,
                        device=0, chunk_length_s=30, return_timestamps=False)
        pipe.model.config.forced_decoder_ids = (
            pipe.tokenizer.get_decoder_prompt_ids(language=lang,
                                                  task='transcribe'))
        for f in clip_files:
            print(f, tag)
            record(f, f'{tag}_orig', fold(pipe(audios[f].copy())['text']))
            if f in stems:
                record(f, f'{tag}_stem', fold(pipe(stems[f].copy())['text']))
        del pipe; torch.cuda.empty_cache()
    except Exception as e:
        print(f'{tag} FAILED: {e}')

# %% NOTE: Indic finetunes output native script (Telugu/Tamil). fold() strips
# non-ascii, so if outputs above look empty, re-run this cell to save RAW text
# — Claude will transliterate locally.
from transformers import pipeline
for tag, model_id, lang in (('te_ft', 'vasista22/whisper-telugu-large-v2', 'te'),
                            ('ta_ft', 'vasista22/whisper-tamil-large-v2', 'ta')):
    need = [f for f in clip_files
            if len((out.get(f, {}).get(f'{tag}_orig') or '').strip()) < 8]
    if not need:
        continue
    try:
        pipe = pipeline('automatic-speech-recognition', model=model_id,
                        device=0, chunk_length_s=30)
        pipe.model.config.forced_decoder_ids = (
            pipe.tokenizer.get_decoder_prompt_ids(language=lang,
                                                  task='transcribe'))
        for f in need:
            print(f, tag, 'raw')
            record(f, f'{tag}_orig_raw', pipe(audios[f].copy())['text'])
            if f in stems:
                record(f, f'{tag}_stem_raw', pipe(stems[f].copy())['text'])
        del pipe; torch.cuda.empty_cache()
    except Exception as e:
        print(f'{tag} raw FAILED: {e}')

# %% D: large-v3 on stems (the proven Tulasi cracker) — for the record
import whisper
wm = whisper.load_model('large-v3')
for f in clip_files:
    if f not in stems:
        continue
    best = ''
    for lang in (None, 'ta', 'te'):
        try:
            t = fold(wm.transcribe(stems[f], language=lang, fp16=True)['text'])
            if len(t) > len(best): best = t
        except Exception as e:
            print('  err', lang, e)
    record(f, 'lv3_stem', best)

# %% Download
files.download('transcripts_indic.json')
