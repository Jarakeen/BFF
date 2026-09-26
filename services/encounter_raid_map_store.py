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
import os
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_LAYOUT_SUFFIXES = {".json"}


class RaidMapManifestRowPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    map_id: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=240)
    relative_path: str = Field(min_length=1, max_length=2000)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Raid Map relative_path must stay inside user data")
        if path.suffix.casefold() not in SUPPORTED_IMAGE_SUFFIXES:
            raise ValueError("Raid Map manifest may contain only supported image paths")
        return value


class RaidMapManifestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: int = Field(default=1, ge=1, le=1)
    encounters: dict[str, list[RaidMapManifestRowPayload]] = Field(default_factory=dict)

    @field_validator("encounters")
    @classmethod
    def validate_encounters(
        cls, value: dict[str, list[RaidMapManifestRowPayload]]
    ) -> dict[str, list[RaidMapManifestRowPayload]]:
        for encounter_id, rows in value.items():
            key = str(encounter_id or "").strip()
            if not key or any(part in key for part in ("/", "\\", "..")):
                raise ValueError(f"invalid Raid Map encounter id: {encounter_id!r}")
            map_ids = [row.map_id.casefold() for row in rows]
            if len(map_ids) != len(set(map_ids)):
                raise ValueError(f"duplicate Raid Map id in encounter {encounter_id!r}")
        return value


def _validated_manifest(payload: object) -> dict:
    return RaidMapManifestPayload.model_validate(payload).model_dump(mode="json")


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
        self.plan_layout_root = self.data_dir / "raid_maps" / "plans"
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
        try:
            return _validated_manifest(payload)
        except (ValidationError, ValueError) as exc:
            raise RuntimeError(f"Raid Map manifest failed Pydantic validation: {exc}") from exc

    def _write_manifest(self, payload: dict) -> None:
        persisted = _validated_manifest(payload)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.manifest_path.parent,
                prefix=f".{self.manifest_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                json.dump(persisted, handle, indent=2, ensure_ascii=False, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.manifest_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        try:
            read_back = _validated_manifest(
                json.loads(self.manifest_path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise RuntimeError(f"Raid Map manifest failed read-back validation: {exc}") from exc
        if read_back != persisted:
            raise RuntimeError("Raid Map manifest did not round-trip exactly")

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
            relative_path = str(raw.get("relative_path", ""))
            if Path(relative_path).suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                # Legacy Phase 14 builds accidentally registered editable JSON
                # layouts in the boss image manifest. Keep those files on disk,
                # but do not offer them to QPixmap-based image viewers.
                continue
            maps.append(
                EncounterRaidMap(
                    map_id=str(raw.get("map_id", "")),
                    encounter_id=encounter_id,
                    label=str(raw.get("label", "") or "Raid Map"),
                    relative_path=relative_path,
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

    def save_plan_layout(
        self,
        plan_id: str,
        source: Path,
        *,
        encounter_id: str = "",
        label: str = "",
    ) -> EncounterRaidMap:
        """Persist the rich editable Raid Map source without registering it as an image.

        Boss-map viewers consume only raster images. Editable JSON belongs to the
        saved Raid Plan and is kept separately so QPixmap never tries to open it.
        """
        plan_key = str(plan_id or "").strip()
        if not plan_key:
            raise ValueError("plan_id is required")
        if any(part in plan_key for part in ("/", "\\", "..")):
            raise ValueError("plan_id must be a stable id, not a path")
        scope = str(encounter_id or "").strip() or f"plan-{plan_key}"
        scope = self._clean_encounter_id(scope)

        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix.lower() not in SUPPORTED_LAYOUT_SUFFIXES:
            raise ValueError("Editable Raid Plan layout must be JSON")

        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
        destination_dir = self.plan_layout_root / plan_key / scope
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{digest}.json"
        if source.resolve() != destination.resolve() and not destination.exists():
            shutil.copy2(source, destination)

        relative = str(destination.relative_to(self.data_dir)).replace("\\", "/")
        return EncounterRaidMap(
            map_id=digest,
            encounter_id=scope,
            label=str(label or "Raid Plan Map").strip() or "Raid Plan Map",
            relative_path=relative,
        )

    def list_plan_layouts(
        self,
        plan_id: str,
        encounter_id: str,
    ) -> tuple[EncounterRaidMap, ...]:
        plan_key = str(plan_id or "").strip()
        if not plan_key:
            return ()
        if any(part in plan_key for part in ("/", "\\", "..")):
            raise ValueError("plan_id must be a stable id, not a path")
        scope = self._clean_encounter_id(encounter_id)
        directory = self.plan_layout_root / plan_key / scope
        if not directory.is_dir():
            return ()
        rows: list[EncounterRaidMap] = []
        for path in sorted(
            directory.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            rows.append(
                EncounterRaidMap(
                    map_id=path.stem,
                    encounter_id=scope,
                    label="Raid Plan Map",
                    relative_path=str(path.relative_to(self.data_dir)).replace("\\", "/"),
                )
            )
        return tuple(rows)

    def latest_plan_layout(
        self,
        plan_id: str,
        encounter_id: str,
    ) -> EncounterRaidMap | None:
        rows = self.list_plan_layouts(plan_id, encounter_id)
        return rows[0] if rows else None

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
