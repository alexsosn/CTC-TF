from __future__ import annotations

import ctypes
import errno
import os
import sys
from pathlib import Path


def publish_stage_noreplace(stage: Path, output: Path) -> None:
    """Atomically publish a staged directory without replacing any destination."""

    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renameat2", None)
        if rename is None:
            raise OSError(errno.ENOTSUP, "atomic no-replace renameat2 unavailable")
        rename.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        rename.restype = ctypes.c_int
        outcome = rename(-100, os.fsencode(stage), -100, os.fsencode(output), 1)
    elif sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, "renamex_np", None)
        if rename is None:
            raise OSError(errno.ENOTSUP, "atomic exclusive renamex_np unavailable")
        rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        rename.restype = ctypes.c_int
        outcome = rename(os.fsencode(stage), os.fsencode(output), 0x00000004)
    elif os.name == "nt":
        os.rename(stage, output)
        return
    else:
        raise OSError(errno.ENOTSUP, "atomic no-replace directory rename unsupported")

    if outcome != 0:
        error = ctypes.get_errno()
        if error in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError(
                error,
                "refusing to overwrite existing Burns output",
                str(output),
            )
        raise OSError(error, os.strerror(error), str(output))
