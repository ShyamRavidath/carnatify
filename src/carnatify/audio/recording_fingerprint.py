"""Optional, local Chromaprint wrapper for recording-copy audits, not raga ID.

The caller supplies a pinned library and finite normalized mono audio blocks.
The native matcher is not used: its randomized alignment tie-breaking is not
part of this deterministic fingerprint extraction contract.
"""
import ctypes as ct
import hashlib
from pathlib import Path

import numpy as np


class RecordingFingerprinter:
    def __init__(self, library, expected_sha256):
        library = Path(library).resolve()
        if hashlib.sha256(library.read_bytes()).hexdigest() != expected_sha256:
            raise ValueError('Fingerprint library checksum mismatch')
        self.lib = ct.CDLL(str(library))
        signatures = {
            'chromaprint_get_version': ([], ct.c_char_p),
            'chromaprint_new': ([ct.c_int], ct.c_void_p),
            'chromaprint_free': ([ct.c_void_p], None),
            'chromaprint_start': ([ct.c_void_p, ct.c_int, ct.c_int], ct.c_int),
            'chromaprint_feed': ([ct.c_void_p, ct.POINTER(ct.c_int16), ct.c_int], ct.c_int),
            'chromaprint_finish': ([ct.c_void_p], ct.c_int),
            'chromaprint_get_raw_fingerprint': ([ct.c_void_p, ct.POINTER(ct.POINTER(ct.c_uint32)), ct.POINTER(ct.c_int)], ct.c_int),
            'chromaprint_get_item_duration_ms': ([ct.c_void_p], ct.c_int),
            'chromaprint_dealloc': ([ct.c_void_p], None),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.lib, name)
            function.argtypes, function.restype = args, result
        if self.lib.chromaprint_get_version().decode() != '1.5.1':
            raise ValueError('Unsupported fingerprint library version')

    def fingerprint(self, blocks, sr=11025):
        if isinstance(sr, bool) or not isinstance(sr, int) or not 8000 <= sr <= 192000:
            raise ValueError('Invalid integer sample rate')
        context = self.lib.chromaprint_new(1)  # TEST2, upstream default
        if not context:
            raise RuntimeError('Cannot allocate fingerprint context')
        output = ct.POINTER(ct.c_uint32)()
        size = ct.c_int()
        samples = 0
        try:
            if not self.lib.chromaprint_start(context, sr, 1):
                raise RuntimeError('Cannot start fingerprint stream')
            for block in blocks:
                y = np.asarray(block)
                if y.ndim != 1 or y.dtype.kind != 'f' or not np.isfinite(y).all():
                    raise ValueError('Fingerprint input must be finite floating-point mono audio')
                if y.size > sr * 60 or (y.size and np.max(np.abs(y)) > 1):
                    raise ValueError('Fingerprint blocks must be normalized and at most 60 seconds')
                if not y.size:
                    continue
                pcm = np.ascontiguousarray(np.rint(y * 32767), dtype=np.int16)
                if not self.lib.chromaprint_feed(context, pcm.ctypes.data_as(ct.POINTER(ct.c_int16)), len(pcm)):
                    raise RuntimeError('Fingerprint feed failed')
                samples += len(pcm)
            if samples < sr * 10:
                raise ValueError('At least ten seconds of audio is required')
            if not self.lib.chromaprint_finish(context):
                raise RuntimeError('Fingerprint finish failed')
            if not self.lib.chromaprint_get_raw_fingerprint(context, ct.byref(output), ct.byref(size)):
                raise RuntimeError('Cannot obtain fingerprint')
            if size.value <= 0:
                raise RuntimeError('Empty fingerprint')
            values = np.ctypeslib.as_array(output, shape=(size.value,)).copy()
            return values, dict(version='1.5.1', algorithm=1, samples=samples, sr=sr,
                                item_duration_ms=self.lib.chromaprint_get_item_duration_ms(context))
        finally:
            if output:
                self.lib.chromaprint_dealloc(output)
            self.lib.chromaprint_free(context)
