from __future__ import annotations

import json
from pathlib import Path


class AchievementProgressService:
    """Tracks which achievement IDs are marked complete, locally, regardless
    of whether Google Sheets sync is configured. This is the source of truth
    for what the checkboxes show; Google Sheets sync (when configured) is an
    additional push/pull on top of this, not a replacement for it."""

    def __init__(self, progress_path: Path) -> None:
        self.progress_path = progress_path
        self._completed_ids: set[str] | None = None

    def _ensure_loaded(self) -> None:
        if self._completed_ids is not None:
            return
        if not self.progress_path.exists():
            self._completed_ids = set()
            return
        try:
            data = json.loads(self.progress_path.read_text(encoding="utf-8"))
            self._completed_ids = set(str(i) for i in data.get("Completed", []))
        except (json.JSONDecodeError, OSError):
            self._completed_ids = set()

    def is_complete(self, achievement_id: str) -> bool:
        self._ensure_loaded()
        return str(achievement_id) in self._completed_ids

    def set_complete(self, achievement_id: str, complete: bool) -> None:
        self._ensure_loaded()
        achievement_id = str(achievement_id)
        if complete:
            self._completed_ids.add(achievement_id)
        else:
            self._completed_ids.discard(achievement_id)
        self._save()

    def completed_count(self) -> int:
        self._ensure_loaded()
        return len(self._completed_ids)

    def _save(self) -> None:
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"Completed": sorted(self._completed_ids)}
        self.progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
