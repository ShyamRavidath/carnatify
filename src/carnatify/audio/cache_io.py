"""Atomic writes for derived audio features, never raw recordings."""
import os
from pathlib import Path
import tempfile
import numpy as np


def atomic_npz(path,**arrays):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.'+target.name+'.',suffix='.tmp',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            np.savez_compressed(stream,**arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,target)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
