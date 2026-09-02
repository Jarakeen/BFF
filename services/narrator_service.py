# services/narrator_service.py
from __future__ import annotations

import json
import random
import re
from pathlib import Path


class NarratorService:
    """Read Natural History Narrator content for the optional Broadcast module.

    JSON is the canonical runtime format. Markdown remains supported as a
    backward-compatible authoring/reference format while the Broadcast module
    is being separated from the core application.

    Public API:
        categories()
        pick(category)
    """

    def __init__(self, content_path: Path):
        self.content_path = Path(content_path)

    def _load(self) -> dict[str, list[str]]:
        if not self.content_path.exists():
            return {}
        if self.content_path.suffix.casefold() == ".json":
            return self._load_json()
        return self._load_markdown()

    def _load_json(self) -> dict[str, list[str]]:
        try:
            data = json.loads(self.content_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        categories: dict[str, list[str]] = {}
        for key, values in data.items():
            if not isinstance(key, str) or not isinstance(values, list):
                continue
            lines = [str(value).strip() for value in values if str(value).strip()]
            categories[key.strip()] = lines
        return categories

    def _load_markdown(self) -> dict[str, list[str]]:
        try:
            text = self.content_path.read_text(encoding="utf-8")
        except OSError:
            return {}

        categories: dict[str, list[str]] = {}
        current = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("##"):
                heading = re.sub(r"^##\s*", "", line)
                heading = re.sub(r"^[^\w]+", "", heading).strip()
                current = heading
                categories[current] = []
                continue
            if current and line.startswith("-"):
                categories[current].append(line[1:].strip())
        return categories

    def categories(self) -> list[str]:
        return list(self._load().keys())

    def pick(self, category: str) -> str:
        choices = self._load().get(category, [])
        if not choices:
            return ""
        return random.choice(choices)
