"""Build the v2 ASR cache for a clip folder (full re-ASR, raw preserved).

For every audio file: sha256 -> whisper large-v3-turbo per-language passes on
the mix (auto/ta/te/hi) and on the demucs vocal stem (auto/ta/te), storing the
RAW text of every hypothesis (native script preserved), segment times, and
per-pass status. Incremental atomic writes after each clip, so an interrupted
run resumes where it stopped.

This is the expensive step of Phase 0 — run caffeinated:
  caffeinate -dims venv_train/bin/python scripts/build_asr_cache_v2.py ~/sung_tests

The resulting cache is keyed by audio hash + full ASR config id
(identify_clip.asr_config_id) and read by identify_clip.py --cache-v2.
Synth/control entries from the old filename-keyed caches never enter here:
only files physically present in the target folder are transcribed
(OPEN_DECISIONS #8 strip happens by construction).
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import identify_clip as ic  # noqa: E402

AUDIO_EXTS = ('.wav', '.mp3', '.m4a', '.flac')


def build(folder: Path) -> None:
    import librosa
    files = sorted(p for p in folder.iterdir()
                   if p.suffix.lower() in AUDIO_EXTS)
    if not files:
        sys.exit(f'no audio files in {folder}')
    cache = ic.load_cache_v2()
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
        hyps = []
        for h in ic._whisper_hyps(mix.astype('float32'),
                                  langs=(None, 'ta', 'te', 'hi')):
            h['source'] = 'mix'
            hyps.append(h)
        try:
            v16 = ic._vocal_stem_16k(p)
            for h in ic._whisper_hyps(v16, langs=(None, 'ta', 'te')):
                h['source'] = 'stem'
                hyps.append(h)
        except Exception as e:
            hyps.append({'source': 'stem', 'lang': 'auto', 'raw': '',
                         'segments': [],
                         'status': f'error: separation failed: {e}'})
        cache['entries'][key] = {
            'file': p.name,
            'audio_sha256': sha,
            'config_id': ic.asr_config_id(),
            'hypotheses': hyps,
        }
        ic._atomic_write_json(ic.CACHE2, cache)
        done += 1
        print(f'[{i}/{len(files)}] {p.name}  '
              f'({time.time() - t0:.0f}s, total {done} new)', flush=True)
    print(f'done: {done} transcribed, {skipped} already cached, '
          f'{(time.time() - t_start) / 60:.1f} min', flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('usage: build_asr_cache_v2.py <clip-folder>')
    build(Path(sys.argv[1]).expanduser())
