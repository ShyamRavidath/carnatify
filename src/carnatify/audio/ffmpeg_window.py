"""Explicit experimental decoder fallback; not enabled in the query frontend."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import numpy as np
import soundfile as sf


def decode_native_window(path,start_s,duration_s):
    """Accurate output-side seek, native channels/rate, <=180s float PCM.

    No tolerant salvage flags, automatic normalization, downmix or resampling.
    Temporary output is byte-bounded; failures never return partial audio.
    """
    if not np.isfinite(start_s) or start_s<0 or not np.isfinite(duration_s) or not 0<duration_s<=180:
        raise ValueError('Invalid bounded FFmpeg window')
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise RuntimeError('FFmpeg and ffprobe are required')
    probe=subprocess.run([ffprobe,'-v','error','-select_streams','a:0','-show_entries',
        'stream=sample_rate,channels','-of','json',str(Path(path).resolve())],
        capture_output=True,check=True,timeout=30)
    stream=json.loads(probe.stdout)['streams'][0]
    sr=int(stream['sample_rate']);channels=int(stream['channels'])
    expected_bytes=int(np.ceil(duration_s*sr))*channels*4
    if not 1<=channels<=32 or not 1<=sr<=384000 or expected_bytes>512*1024**2:
        raise ValueError('Native window exceeds decoder resource bounds')
    with tempfile.TemporaryDirectory(prefix='carnatify-decode-') as folder:
        output=Path(folder)/'window.wav'
        with tempfile.TemporaryFile() as errors:
            result=subprocess.run([ffmpeg,'-nostdin','-v','error','-xerror','-threads','1',
                '-i',str(Path(path).resolve()),'-ss',str(float(start_s)),'-t',str(float(duration_s)),
                '-map','0:a:0','-c:a','pcm_f32le','-fs',str(expected_bytes+65536),str(output)],
                stdout=subprocess.DEVNULL,stderr=errors,timeout=120,check=False)
            size=errors.tell();errors.seek(0);message=errors.read(4096).decode('utf8',errors='replace')
        if result.returncode:raise RuntimeError(f'FFmpeg window failed ({result.returncode}): {message}')
        data,actual_sr=sf.read(output,dtype='float32',always_2d=True)
    if actual_sr!=sr or data.shape[1]!=channels or len(data)>int(np.ceil(duration_s*sr))+1:
        raise ValueError('Unexpected native decoder output layout')
    if not data.size or not np.isfinite(data).all():raise ValueError('Empty or non-finite decoder output')
    return data,sr,dict(decoder='ffmpeg_strict_output_seek',stderr_bytes=size,
        stderr_excerpt=message,start_s=float(start_s),requested_duration_s=float(duration_s))
