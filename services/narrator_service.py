from __future__ import annotations

import json
import random
from pathlib import Path


class NarratorService:
    """Reads the Natural History Narrator content bank and picks random lines.

    The content file is plain JSON (category -> list of lines) so the person
    can add/edit lines themselves without touching any code.
    """

    def __init__(self, content_path: Path) -> None:
        self.content_path = content_path

    def _load(self) -> dict:
        if not self.content_path.exists():
            return {}
        try:
            return json.loads(self.content_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def pick(self, category: str) -> str:
        content = self._load()
        lines = content.get(category) or []
        if not lines:
            return ""
        return random.choice(lines)
