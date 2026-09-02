# services/achievement_progress_service.py
from __future__ import annotations

import json
from pathlib import Path


class AchievementProgressService:
    """Profile-aware local achievement progress.

    Local progress remains the source of truth for achievement checkboxes.
    External spreadsheet/Google Sheets integrations can import or synchronize
    completed IDs into named profiles without replacing this persistence layer.

    Legacy files with a top-level ``Completed`` list are migrated in memory to
    a neutral ``Default`` profile and written in the new format on the next
    change. We deliberately do not guess which person owned legacy progress.
    """

    VERSION = 2
    DEFAULT_PROFILE = "Default"

    def __init__(self, progress_path: Path) -> None:
        self.progress_path = Path(progress_path)
        self._profiles: dict[str, set[str]] | None = None
        self._active_profile = self.DEFAULT_PROFILE

    def _ensure_loaded(self) -> None:
        if self._profiles is not None:
            return

        self._profiles = {}
        if self.progress_path.exists():
            try:
                data = json.loads(self.progress_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError, TypeError):
                data = {}

            raw_profiles = data.get("Profiles")
            if isinstance(raw_profiles, dict):
                for raw_name, raw_progress in raw_profiles.items():
                    name = self._normalize_profile_name(raw_name)
                    if not name or not isinstance(raw_progress, dict):
                        continue
                    completed = raw_progress.get("Completed", [])
                    if not isinstance(completed, list):
                        completed = []
                    self._profiles[name] = {str(value) for value in completed}

                requested = self._normalize_profile_name(data.get("ActiveProfile"))
                if requested in self._profiles:
                    self._active_profile = requested
            else:
                # Version-1 compatibility: keep the old completion set intact,
                # but do not attribute it to a named person without evidence.
                completed = data.get("Completed", [])
                if not isinstance(completed, list):
                    completed = []
                self._profiles[self.DEFAULT_PROFILE] = {
                    str(value) for value in completed
                }

        if not self._profiles:
            self._profiles[self.DEFAULT_PROFILE] = set()

        if self._active_profile not in self._profiles:
            self._active_profile = next(iter(self._profiles))

    def reload(self, *, preserve_active_profile: bool = True) -> None:
        """Reload progress from disk after another service instance writes it.

        The application has multiple UI surfaces that can own separate
        ``AchievementProgressService`` instances. Local workbook import is one
        such writer, so long-lived readers need an explicit cache invalidation
        point before repainting their UI.
        """
        previous = self._active_profile if preserve_active_profile else self.DEFAULT_PROFILE
        self._profiles = None
        self._active_profile = self.DEFAULT_PROFILE
        self._ensure_loaded()
        if preserve_active_profile:
            normalized = self._normalize_profile_name(previous)
            if normalized in self._profiles:
                self._active_profile = normalized

    @staticmethod
    def _normalize_profile_name(name) -> str:
        return " ".join(str(name or "").strip().split())

    @property
    def active_profile(self) -> str:
        self._ensure_loaded()
        return self._active_profile

    def profiles(self) -> list[str]:
        self._ensure_loaded()
        return list(self._profiles)

    def ensure_profile(self, name: str) -> str:
        self._ensure_loaded()
        normalized = self._normalize_profile_name(name)
        if not normalized:
            raise ValueError("Profile name cannot be empty.")
        if normalized not in self._profiles:
            self._profiles[normalized] = set()
            self._save()
        return normalized

    def set_active_profile(self, name: str) -> str:
        normalized = self.ensure_profile(name)
        if normalized != self._active_profile:
            self._active_profile = normalized
            self._save()
        return self._active_profile

    def is_complete(self, achievement_id: str) -> bool:
        self._ensure_loaded()
        return str(achievement_id) in self._profiles[self._active_profile]

    def set_complete(self, achievement_id: str, complete: bool) -> None:
        self._ensure_loaded()
        achievement_id = str(achievement_id)
        completed = self._profiles[self._active_profile]
        if complete:
            completed.add(achievement_id)
        else:
            completed.discard(achievement_id)
        self._save()

    def completed_ids(self, profile: str | None = None) -> set[str]:
        self._ensure_loaded()
        profile_name = self._active_profile if profile is None else self._normalize_profile_name(profile)
        if profile_name not in self._profiles:
            return set()
        return set(self._profiles[profile_name])

    def completed_count(self, profile: str | None = None) -> int:
        return len(self.completed_ids(profile))

    def merge_completed(self, profile: str, achievement_ids) -> int:
        """Add imported completion IDs to a profile without deleting local data."""
        profile_name = self.ensure_profile(profile)
        before = len(self._profiles[profile_name])
        self._profiles[profile_name].update(str(value) for value in achievement_ids)
        added = len(self._profiles[profile_name]) - before
        if added:
            self._save()
        return added

    def replace_completed(self, profile: str, achievement_ids) -> None:
        """Replace one profile's completion set when an explicit full sync asks for it."""
        profile_name = self.ensure_profile(profile)
        self._profiles[profile_name] = {str(value) for value in achievement_ids}
        self._save()

    def _save(self) -> None:
        self._ensure_loaded()
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "Version": self.VERSION,
            "ActiveProfile": self._active_profile,
            "Profiles": {
                name: {"Completed": sorted(completed)}
                for name, completed in self._profiles.items()
            },
        }
        self.progress_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
