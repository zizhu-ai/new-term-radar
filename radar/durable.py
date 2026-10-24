"""Atomic text/bytes writes with a size check, so a crash mid-write cannot leave a
half-written report that later looks like a successful run.
"""
from __future__ import annotations

import os
from pathlib import Path


def write_text(path: Path | str, text: str, *, encoding: str = "utf-8") -> Path:
    """Write `text` to `path` via a sibling temp file + os.replace, then verify size."""
    data = text.encode(encoding)
    return write_bytes(path, data)


def write_bytes(path: Path | str, data: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    got = path.stat().st_size
    if got != len(data):
        raise OSError(f"durable write verify failed: {path} size {got} != {len(data)}")
    return path
