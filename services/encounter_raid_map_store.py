from __future__ import annotations

"""User-owned Raid Map persistence keyed by boss-guide encounter id.

Raid maps are not canonical encounter truth. They live beside other user data so
an ESO database refresh cannot overwrite or delete the user's saved diagrams.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil


SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class EncounterRaidMap:
    map_id: str
    encounter_id: str
    label: str
    relative_path: str


class EncounterRaidMapStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.root = self.data_dir / "raid_maps" / "bosses"
        self.manifest_path = self.data_dir / "raid_maps" / "boss_maps.json"

    @staticmethod
    def _clean_encounter_id(encounter_id: str) -> str:
        value = str(encounter_id or "").strip()
        if not value:
            raise ValueError("encounter_id is required")
        if any(part in value for part in ("/", "\\", "..")):
            raise ValueError("encounter_id must be a canonical id, not a path")
        return value

    def _read_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"schema_version": 1, "encounters": {}}
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unable to read Raid Map manifest: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Raid Map manifest must contain a JSON object")
        encounters = payload.get("encounters", {})
        if not isinstance(encounters, dict):
            raise RuntimeError("Raid Map manifest encounters must be an object")
        return {"schema_version": 1, "encounters": encounters}

    def _write_manifest(self, payload: dict) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.manifest_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.manifest_path)

    def list_maps(self, encounter_id: str) -> tuple[EncounterRaidMap, ...]:
        encounter_id = self._clean_encounter_id(encounter_id)
        payload = self._read_manifest()
        rows = payload["encounters"].get(encounter_id, [])
        if not isinstance(rows, list):
            raise RuntimeError(f"Raid Map manifest entry for {encounter_id!r} must be a list")
        maps = []
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            maps.append(
                EncounterRaidMap(
                    map_id=str(raw.get("map_id", "")),
                    encounter_id=encounter_id,
                    label=str(raw.get("label", "") or "Raid Map"),
                    relative_path=str(raw.get("relative_path", "")),
                )
            )
        return tuple(sorted(maps, key=lambda row: (row.label.casefold(), row.map_id)))

    def resolve_path(self, raid_map: EncounterRaidMap) -> Path:
        candidate = self.data_dir / raid_map.relative_path
        return candidate.resolve()

    def import_map(
        self,
        encounter_id: str,
        source: Path,
        *,
        label: str = "",
    ) -> EncounterRaidMap:
        encounter_id = self._clean_encounter_id(encounter_id)
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        suffix = source.suffix.lower()
        if suffix not in SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError(
                "Raid Map image must be PNG, JPG, JPEG, or WebP; "
                f"got {source.suffix or '(no extension)'}"
            )

        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
        destination_dir = self.root / encounter_id
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{digest}{suffix}"
        if source.resolve() != destination.resolve() and not destination.exists():
            shutil.copy2(source, destination)

        relative = str(destination.relative_to(self.data_dir)).replace("\\", "/")
        record = EncounterRaidMap(
            map_id=digest,
            encounter_id=encounter_id,
            label=str(label or source.stem or "Raid Map").strip() or "Raid Map",
            relative_path=relative,
        )

        payload = self._read_manifest()
        rows = payload["encounters"].setdefault(encounter_id, [])
        replacement = {
            "map_id": record.map_id,
            "label": record.label,
            "relative_path": record.relative_path,
        }
        for index, raw in enumerate(rows):
            if isinstance(raw, dict) and str(raw.get("map_id", "")) == record.map_id:
                rows[index] = replacement
                break
        else:
            rows.append(replacement)
        self._write_manifest(payload)
        return record

    def remove_map(self, encounter_id: str, map_id: str) -> bool:
        encounter_id = self._clean_encounter_id(encounter_id)
        map_id = str(map_id or "").strip()
        if not map_id:
            return False
        payload = self._read_manifest()
        rows = payload["encounters"].get(encounter_id, [])
        if not isinstance(rows, list):
            return False

        removed = None
        kept = []
        for raw in rows:
            if (
                removed is None
                and isinstance(raw, dict)
                and str(raw.get("map_id", "")) == map_id
            ):
                removed = raw
                continue
            kept.append(raw)
        if removed is None:
            return False

        if kept:
            payload["encounters"][encounter_id] = kept
        else:
            payload["encounters"].pop(encounter_id, None)
        self._write_manifest(payload)

        relative_path = str(removed.get("relative_path", "") or "")
        if relative_path:
            candidate = (self.data_dir / relative_path).resolve()
            root = self.root.resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                return True
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass
        return True
