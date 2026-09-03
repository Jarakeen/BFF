from __future__ import annotations

"""Profile-aware Antiquities catalog harvested from the UESP antiquityLeads export."""

import json
from pathlib import Path


class AntiquityService:
    DEFAULT_PROFILE = "Default"

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.catalog_path = self.data_dir / "antiquities.json"
        self.progress_path = self.data_dir / "antiquity_progress.json"
        self._active_profile = self.DEFAULT_PROFILE
        self._records: list[dict] = []
        self._by_id: dict[int, dict] = {}
        self._progress: dict[str, dict[str, dict]] = {}
        self.available = False
        self.bootstrap_message = ""
        self._load()

    @staticmethod
    def _normalize_profile_name(name) -> str:
        return " ".join(str(name or "").strip().split())

    @property
    def active_profile(self) -> str:
        return self._active_profile

    def ensure_profile(self, name: str) -> str:
        normalized = self._normalize_profile_name(name)
        if not normalized:
            raise ValueError("Profile name cannot be empty.")
        self._progress.setdefault(normalized, {})
        return normalized

    def set_active_profile(self, name: str) -> str:
        self._active_profile = self.ensure_profile(name)
        return self._active_profile

    def _load(self) -> None:
        try:
            payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            self._records = list(payload.get("records") or [])
            self._by_id = {int(row["id"]): row for row in self._records}
            self.available = bool(self._records)
            self.bootstrap_message = (
                f"Antiquities catalog ready ({len(self._records):,} records)."
                if self.available
                else "Antiquities reference data is empty."
            )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.bootstrap_message = f"Antiquities reference data unavailable: {exc}"
            self.available = False
            return

        if self.progress_path.exists():
            try:
                payload = json.loads(self.progress_path.read_text(encoding="utf-8"))
                profiles = payload.get("profiles") if isinstance(payload, dict) else {}
                if isinstance(profiles, dict):
                    self._progress = {
                        str(profile): dict(entries or {})
                        for profile, entries in profiles.items()
                        if str(profile).strip() and isinstance(entries, dict)
                    }
            except (OSError, ValueError, TypeError):
                self._progress = {}
        self._progress.setdefault(self.DEFAULT_PROFILE, {})

    def _save_progress(self) -> None:
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.progress_path.with_suffix(self.progress_path.suffix + ".tmp")
        payload = {"schema_version": 1, "profiles": self._progress}
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.progress_path)

    def profiles(self) -> list[str]:
        names = sorted(self._progress, key=str.casefold)
        if self.DEFAULT_PROFILE in names:
            names.remove(self.DEFAULT_PROFILE)
        return [self.DEFAULT_PROFILE, *names]

    def _state(self, antiquity_id: int) -> dict:
        return dict(self._progress.get(self._active_profile, {}).get(str(int(antiquity_id)), {}) or {})

    def progress_summary(self) -> tuple[int, int]:
        if not self.available:
            return 0, 0
        entries = self._progress.get(self._active_profile, {})
        recovered = sum(
            1 for row in self._records
            if bool((entries.get(str(int(row["id"]))) or {}).get("recovered"))
        )
        return recovered, len(self._records)

    def items(self, query: str = "") -> list[dict]:
        if not self.available:
            return []
        needle = str(query or "").strip().casefold()
        result = []
        for source in self._records:
            if needle:
                haystack = " ".join(
                    [
                        str(source.get("name") or ""),
                        str(source.get("category_name") or ""),
                        str(source.get("set_name") or ""),
                        *[
                            f"{entry.get('speaker', '')} {entry.get('text', '')}"
                            for entry in source.get("lore") or []
                        ],
                    ]
                ).casefold()
                if needle not in haystack:
                    continue
            row = dict(source)
            state = self._state(int(row["id"]))
            row["owned"] = bool(state.get("recovered"))
            row["acquired_on"] = str(state.get("recovered_on") or "")
            row["notes"] = str(state.get("notes") or "")
            result.append(row)
        return result

    def item(self, antiquity_id: int) -> dict | None:
        source = self._by_id.get(int(antiquity_id))
        if source is None:
            return None
        row = dict(source)
        state = self._state(int(antiquity_id))
        row["owned"] = bool(state.get("recovered"))
        row["acquired_on"] = str(state.get("recovered_on") or "")
        row["notes"] = str(state.get("notes") or "")
        return row

    def set_progress(self, antiquity_id: int, *, recovered: bool, recovered_on: str = "", notes: str = "") -> None:
        antiquity_id = int(antiquity_id)
        if antiquity_id not in self._by_id:
            raise KeyError(f"Unknown antiquity ID: {antiquity_id}")
        profile = self.ensure_profile(self._active_profile)
        self._progress[profile][str(antiquity_id)] = {
            "recovered": bool(recovered),
            "recovered_on": str(recovered_on or "").strip(),
            "notes": str(notes or "").strip(),
        }
        self._save_progress()

    def set_recovered_batch(self, recovered_by_id: dict[int, bool]) -> int:
        if not recovered_by_id:
            return 0
        profile = self.ensure_profile(self._active_profile)
        entries = self._progress[profile]
        count = 0
        for raw_id, recovered in recovered_by_id.items():
            antiquity_id = int(raw_id)
            if antiquity_id not in self._by_id:
                continue
            key = str(antiquity_id)
            existing = dict(entries.get(key) or {})
            existing["recovered"] = bool(recovered)
            existing.setdefault("recovered_on", "")
            existing.setdefault("notes", "")
            entries[key] = existing
            count += 1
        self._save_progress()
        return count

    def close(self) -> None:
        return
