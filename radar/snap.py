"""Snapshots: yesterday's state of each signal, gzip JSON files in the state directory."""
from __future__ import annotations

import gzip
import json
from pathlib import Path


def load(path: Path):
    if _PENDING is not None and Path(path) in _PENDING:
        return json.loads(json.dumps(_PENDING[Path(path)]))
    return json.loads(gzip.decompress(path.read_bytes())) if path.exists() else None


# box patch: while deferred, saves are held in memory and written only by commit(), so a run
# that fails before the name judge has scored the terms does not mark them as seen.
_PENDING: dict | None = None


def defer() -> None:
    global _PENDING
    _PENDING = {}


def commit() -> int:
    global _PENDING
    held, _PENDING = _PENDING or {}, None
    for path, data in held.items():
        _write(path, data)
    return len(held)


def discard() -> int:
    global _PENDING
    n, _PENDING = len(_PENDING or {}), None
    return n


def save(path: Path, data) -> None:
    if _PENDING is not None:
        _PENDING[Path(path)] = data
        return
    _write(path, data)


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(data, ensure_ascii=False).encode()))
