from __future__ import annotations

"""Atomic crash-recovery drafts kept outside committed application state."""

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.config import get_user_data_dir


class UiDraftRecoveryService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or (get_user_data_dir() / "drafts"))

    @staticmethod
    def _safe_key(key: object) -> str:
        value = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(key or "").strip())
        return value.strip("-._") or "draft"

    def path_for(self, key: object) -> Path:
        return self.root / f"{self._safe_key(key)}.json"

    def save(self, key: object, payload: dict[str, Any]) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(key)
        envelope = {
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "payload": payload,
        }
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=self.root,
            text=True,
        )
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(envelope, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            temp.replace(path)
        finally:
            if temp.exists():
                temp.unlink()
        return path

    def load(self, key: object) -> dict[str, Any] | None:
        path = self.path_for(key)
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return None
        return value if isinstance(value, dict) else None

    def discard(self, key: object) -> None:
        try:
            self.path_for(key).unlink()
        except FileNotFoundError:
            pass

    def list_drafts(self) -> tuple[Path, ...]:
        if not self.root.is_dir():
            return ()
        return tuple(
            sorted(
                self.root.glob("*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        )


__all__ = ["UiDraftRecoveryService"]
