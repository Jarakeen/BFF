"""Robust persistence helpers for BuildService.

The Builds page stores user-owned roster data in data/builds.json.
This module keeps the persistence hardening separate from the large
BuildService export surface while preserving its public API.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from models.build_model import BuildRoster


def load(service) -> BuildRoster:
    """Load a roster without silently converting corruption into an empty roster."""
    path = Path(service.builds_path)
    if not path.exists():
        return BuildRoster()

    data = json.loads(path.read_text(encoding="utf-8"))
    return BuildRoster.from_dict(data)


def save(service, roster: BuildRoster) -> None:
    """Atomically save a roster and verify the written bytes round-trip."""
    path = Path(service.builds_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        roster.to_dict(),
        ensure_ascii=False,
        indent=2,
    )

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )

    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

        temp_path.replace(path)

        # Verify the exact serialized representation can be read back.
        written = json.loads(path.read_text(encoding="utf-8"))
        if written != roster.to_dict():
            raise IOError(
                f"Build persistence verification failed for {path.resolve()}"
            )
    finally:
        if temp_path.exists():
            temp_path.unlink()
