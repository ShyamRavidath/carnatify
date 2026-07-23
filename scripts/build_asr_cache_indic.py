"""Build the Rung-3 IndicConformer ASR cache for a clip folder.

Model: ai4bharat/indic-conformer-600m-multilingual through its OFFICIAL
native-ONNX path (assets/preprocessor.ts -> assets/encoder.onnx ->
assets/ctc_decoder.onnx), greedy CTC decode only — the decode loop below is
a line-for-line port of `_ctc_decode` in the repo's own model_onnx.py, minus
transformers/AutoModel overhead. No RNNT, no stem/Demucs lane, no VAD, no
segmentation: mix audio only, loaded as a numpy array (no ffmpeg on this
machine).

Language lanes are FIXED for every clip (te, ta, kn, hi, ml — the corpus's
real span; never read from the filename truth). ml is free: the encoder and
CTC head run once per clip, each lane is only a vocab mask + argmax.

Writes data/asr_cache_indic.json — the same v2 schema as the turbo cache
but its own file + config identity (identify_clip.INDIC_CONFIG_ID); the
turbo cache is never touched. Incremental atomic writes; interrupted runs
resume. status: 'ok' | 'empty' | 'error: ...' — an integration failure is
NEVER recorded as an ASR-dead clip.

Model weights: gated on HF (gated=auto, MIT license). Either
  huggingface-cli login   (accept the gate on the ai4bharat repo page), or
  CARNATIFY_INDIC_REPO=<ungated mirror id>
then run
  venv_train/bin/python scripts/build_asr_cache_indic.py --download
Full run (long — keep the lid open):
  caffeinate -dims venv_train/bin/python -u scripts/build_asr_cache_indic.py ~/sung_tests
Smoke test (integration only, no capability claim):
  ... build_asr_cache_indic.py ~/sung_tests nagumomu Devadideva
"""
import json
import os
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ['CARNATIFY_ASR_BACKEND'] = 'indic'

import identify_clip as ic  # noqa: E402

AUDIO_EXTS = ('.wav', '.mp3', '.m4a', '.flac')
LANGS = tuple(ic.ASR_CONFIG_INDIC['mix_langs'])
REPO = os.environ.get('CARNATIFY_INDIC_REPO',
                      'ai4bharat/indic-conformer-600m-multilingual')
CTC_PATTERNS = dict(
    allow_patterns=['config.json', 'model_onnx.py', 'README.md', 'assets/*'],
    ignore_patterns=['assets/joint_*', 'assets/rnnt_decoder*'])


def model_dir() -> Path:
    override = os.environ.get('CARNATIFY_INDIC_MODEL_DIR')
    if override:
        return Path(override).expanduser()
    from huggingface_hub import snapshot_download
    return Path(snapshot_download(REPO, local_files_only=True,
                                  **CTC_PATTERNS))


class IndicCTC:
    """Official ONNX CTC path, encoder shared across language lanes."""

    def __init__(self, folder: Path):
        import onnxruntime as ort
        import torch
        self._torch = torch
        a = folder / 'assets'
        self.pre = torch.jit.load(str(a / 'preprocessor.ts'),
                                  map_location='cpu')
        opts = ort.SessionOptions()
        self.enc = ort.InferenceSession(str(a / 'encoder.onnx'), opts,
                                        providers=['CPUExecutionProvider'])
        self.ctc = ort.InferenceSession(str(a / 'ctc_decoder.onnx'), opts,
                                        providers=['CPUExecutionProvider'])
        self.vocab = json.loads((a / 'vocab.json').read_text())
        self.masks = json.loads((a / 'language_masks.json').read_text())
        cfg = {}
        cfg_path = folder / 'config.json'
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
        self.blank_id = cfg.get('BLANK_ID', 256)
        self.frame_s = cfg.get('FRAME_DURATION_MS', 0.08)

    def transcribe(self, wav16, langs=LANGS) -> list[dict]:
        """One hypothesis per language lane from a single encoder pass.
        wav16: float32 numpy mono @16k."""
        torch = self._torch
        wav = torch.tensor(wav16, dtype=torch.float32)[None]
        with torch.no_grad():
            sig, length = self.pre(input_signal=wav,
                                   length=torch.tensor([wav.shape[-1]]))
        enc_out, enc_len = self.enc.run(
            ['outputs', 'encoded_lengths'],
            {'audio_signal': sig.numpy(), 'length': length.numpy()})
        full_logits = self.ctc.run(['logprobs'],
                                   {'encoder_output': enc_out})[0]
        hyps = []
        for lang in langs:
            h = {'source': 'mix', 'lang': lang, 'raw': '', 'segments': [],
                 'status': 'ok'}
            try:
                lp = torch.from_numpy(
                    full_logits[:, :, self.masks[lang]]).log_softmax(dim=-1)
                T = int(enc_len[0])
                path = lp[0, :T].argmax(dim=-1)
                # word-level timestamps off the same greedy path ('▁' marks
                # word starts in the sentencepiece vocab)
                words, word, t0, t1 = [], '', 0.0, 0.0
                prev = None
                for f, tok in enumerate(path.tolist()):
                    if tok == self.blank_id or tok == prev:
                        prev = tok if tok != self.blank_id else None
                        continue
                    prev = tok
                    piece = self.vocab[lang][tok]
                    if '▁' in piece:
                        if word:
                            words.append((word, t0, t1))
                        word, t0 = piece.replace('▁', ''), f * self.frame_s
                    else:
                        word += piece
                    t1 = (f + 1) * self.frame_s
                if word:
                    words.append((word, t0, t1))
                h['raw'] = ' '.join(w for w, _, _ in words).strip()
                h['segments'] = [{'start': round(a, 2), 'end': round(b, 2),
                                  'text': w} for w, a, b in words]
                if not h['raw']:
                    h['status'] = 'empty'
            except Exception as e:
                h['status'] = f'error: {type(e).__name__}: {e}'
                print(f'  (indic lane {lang} failed: {h["status"]})',
                      file=sys.stderr)
            hyps.append(h)
        return hyps


def build(folder: Path, only: list[str]) -> None:
    import librosa
    files = sorted(p for p in folder.iterdir()
                   if p.suffix.lower() in AUDIO_EXTS)
    if only:
        # smoke-test filter; NFC both sides (APFS filenames are NFD)
        wanted = [unicodedata.normalize('NFC', w).lower() for w in only]
        files = [p for p in files
                 if any(w in unicodedata.normalize('NFC', p.name).lower()
                        for w in wanted)]
    if not files:
        sys.exit(f'no matching audio files in {folder}')
    model = IndicCTC(model_dir())
    cache = ic.load_cache_v2()
    assert cache['config'] == ic.ASR_CONFIG_INDIC or not cache['entries'], \
        'refusing to write into a cache with a different config'
    done = skipped = 0
    t_start = time.time()
    for i, p in enumerate(files, 1):
        sha = ic.audio_sha256(p)
        key = ic.cache2_key(sha)
        if key in cache['entries']:
            skipped += 1
            continue
        t0 = time.time()
        mix, _ = librosa.load(str(p), sr=16000, mono=True)
        try:
            hyps = model.transcribe(mix.astype('float32'))
        except Exception as e:
            # whole-clip integration failure: recorded per-lane as error,
            # never as an empty (ASR-dead-looking) hypothesis
            hyps = [{'source': 'mix', 'lang': lang, 'raw': '',
                     'segments': [],
                     'status': f'error: {type(e).__name__}: {e}'}
                    for lang in LANGS]
            print(f'  (indic encode failed on {p.name}: {e})',
                  file=sys.stderr)
        cache['entries'][key] = {
            'file': p.name,
            'audio_sha256': sha,
            'config_id': ic.asr_config_id(),
            'hypotheses': hyps,
        }
        ic._atomic_write_json(ic.INDIC_CACHE, cache)
        done += 1
        ok = sum(1 for h in hyps if h['status'] == 'ok')
        print(f'[{i}/{len(files)}] {p.name}  lanes ok {ok}/{len(hyps)}  '
              f'({time.time() - t0:.0f}s, total {done} new)', flush=True)
    print(f'done: {done} transcribed, {skipped} already cached, '
          f'{(time.time() - t_start) / 60:.1f} min', flush=True)


if __name__ == '__main__':
    if '--download' in sys.argv:
        from huggingface_hub import snapshot_download
        print('downloading CTC subset of', REPO, flush=True)
        print(snapshot_download(REPO, **CTC_PATTERNS))
        sys.exit(0)
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit('usage: build_asr_cache_indic.py <clip-folder> '
                 '[name-filter ...] | --download')
    build(Path(args[0]).expanduser(), args[1:])
