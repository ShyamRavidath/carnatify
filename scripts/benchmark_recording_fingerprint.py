"""Fixed four-recording robustness pilot; no identity labels or model changes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import soundfile as sf
from carnatify.audio.recording_fingerprint import RecordingFingerprinter
from carnatify.audio.utils import load_audio_window
from scripts.raga_pipeline import sha, write_json
from scripts.audit_recording_fingerprint_overlap import POLICY, make_index, scan


def alignment(a, b, max_shift=50, min_frames=160):
    """Mean bit error at bounded integer-frame offsets; no native random ties."""
    best = None
    for shift in range(-max_shift, max_shift + 1):
        ia, ib = max(0, -shift), max(0, shift)
        n = min(len(a) - ia, len(b) - ib)
        if n < min_frames:
            continue
        xor = np.bitwise_xor(a[ia:ia+n], b[ib:ib+n])
        error = float(np.unpackbits(xor.view(np.uint8)).mean())
        candidate = (error, abs(shift), shift, n)
        if best is None or candidate < best:
            best = candidate
    return None if best is None else dict(bit_error=best[0], shift_frames=best[2], overlap_frames=best[3])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'data/overhaul/recording_fingerprint_pilot')
    parser.add_argument('--screen',action='store_true')
    args = parser.parse_args()
    lib = ROOT / 'data/overhaul/chromaprint/build/src/libchromaprint.1.5.1.dylib'
    corpus_path = ROOT / 'data/overhaul/annotated_corpus_v2.json'
    corpus = json.loads(corpus_path.read_text())['rows']
    source = ROOT / 'data/overhaul/saraga_audio_results.json'
    audio_hashes = {r['track']: r['metadata']['audio_sha256'] for r in json.loads(source.read_text())['rows']}
    rows = sorted([r for r in corpus if r['track'] in audio_hashes], key=lambda r: audio_hashes[r['track']])[:4]
    plan = dict(corpus_sha256=sha(corpus_path), audio_receipts_sha256=sha(source), library_sha256=sha(lib),
                selection='first four full-audio SHA256 values; centered 30 seconds',
                transforms=['identity', 'gain_0.35', 'mp3_64k', 'leading_silence_3.7s'],
                alignment=dict(max_shift=50, min_frames=160),
                tracks=[dict(track=r['track'], audio_sha256=audio_hashes[r['track']]) for r in rows])
    if args.screen:plan['screening_policy']=POLICY
    args.out.mkdir(parents=True, exist_ok=True)
    pp = args.out / 'plan.json'
    if pp.exists() and json.loads(pp.read_text()) != plan:
        raise ValueError('Pilot plan changed')
    write_json(pp, plan)
    printer = RecordingFingerprinter(lib, plan['library_sha256'])
    fingerprints, results = [], []
    for row in rows:
        audio = ROOT / row['audio']
        if sha(audio) != audio_hashes[row['track']]:
            raise ValueError('Pilot source audio changed')
        duration = sf.info(audio).duration
        if duration < 30:
            raise ValueError('Fixed pilot recording is shorter than 30s')
        y, sr, diagnostic = load_audio_window(audio, max(0, (duration - 30) / 2), 30, target_sr=22050)
        y = np.clip(y, -1, 1)
        variants = dict(identity=y, gain_0_35=y*.35,
                        leading_silence_3_7s=np.r_[np.zeros(round(sr*3.7), dtype=np.float32), y])
        with tempfile.TemporaryDirectory(prefix='carnatify-fingerprint-') as temporary:
            wav = Path(temporary) / 'source.wav'
            mp3 = Path(temporary) / 'compressed.mp3'
            sf.write(wav, y, sr, subtype='PCM_16')
            subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(wav),'-codec:a','libmp3lame',
                            '-b:a','64k',str(mp3)], check=True, timeout=60)
            decoded, decoded_sr = sf.read(mp3, dtype='float32')
            if decoded_sr != sr or decoded.ndim != 1:
                raise ValueError('Unexpected transcoded sample format')
            variants['mp3_64k'] = np.clip(decoded, -1, 1)
        values = {name: printer.fingerprint([wave], int(sr))[0] for name, wave in variants.items()}
        base = values['identity']
        fingerprints.append(base)
        results.append(dict(track=row['track'], unique_codes=len(np.unique(base)), audio=diagnostic,
                            transforms={name: alignment(base, fp) for name, fp in values.items()}))
        if args.screen:
            index=make_index([base])
            results[-1]['screening_flags']={name:scan(fp,[base],index) for name,fp in values.items()}
    negatives = [dict(a=rows[i]['track'], b=rows[j]['track'], alignment=alignment(fingerprints[i],fingerprints[j]))
                 for i in range(len(rows)) for j in range(i)]
    report = dict(plan_sha256=sha(pp), rows=results, different_recording_pairs=negatives,
                  limitation='Small robustness pilot; not a validated corpus-wide duplicate threshold')
    if args.screen:
        report['different_recording_screening_flags']=[dict(a=rows[i]['track'],b=rows[j]['track'],
            flags=scan(fingerprints[i],[fingerprints[j]],make_index([fingerprints[j]])))
            for i in range(len(rows)) for j in range(i)]
    write_json(args.out / 'result.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
