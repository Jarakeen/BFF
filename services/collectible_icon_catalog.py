from __future__ import annotations

import json
from pathlib import Path


class CollectibleIconCatalog:
    """Resolve harvested collectible IDs to local image files.

    The icon collector owns the manifest format. Runtime code only needs a
    stable ID -> Path lookup and remains usable when the cache is absent.
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.icon_dir = self.data_dir / "collectible_icons"
        self.manifest_path = self.icon_dir / "manifest.json"
        self.entries: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        self.entries = {}
        if not self.manifest_path.exists():
            return

        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        entries = payload.get("entries", {}) if isinstance(payload, dict) else {}
        if isinstance(entries, dict):
            self.entries = {
                str(key): value
                for key, value in entries.items()
                if isinstance(value, dict)
            }

    @property
    def available_count(self) -> int:
        return sum(1 for key in self.entries if self.path_for(key) is not None)

    def path_for(self, collectible_id: int | str) -> Path | None:
        entry = self.entries.get(str(collectible_id))
        if not entry:
            return None

        filename = str(entry.get("file", "") or "").strip()
        if not filename:
            return None

        # The manifest stores basenames relative to collectible_icons. Reject
        # attempts to escape the cache directory if a manifest is malformed.
        candidate = (self.icon_dir / filename).resolve()
        try:
            candidate.relative_to(self.icon_dir.resolve())
        except ValueError:
            return None

        if not candidate.is_file() or candidate.stat().st_size <= 0:
            return None
        return candidate
