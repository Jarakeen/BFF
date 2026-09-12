from __future__ import annotations

"""Persist completed Rotation Builder plans as build-owned user artifacts.

Rotation artifacts are user state, not ESO reference data, so they live beside
builds.json rather than in eso.db.  Records are keyed by the canonical build_id;
character names and build names are display metadata only.
"""

import copy
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def jsonable(value: Any) -> Any:
    """Convert canonical dataclasses/enums into deterministic JSON values."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, set):
        return [jsonable(item) for item in sorted(value, key=lambda item: repr(item))]
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def resolve_canonical_build_id(catalog_service, build) -> str | None:
    """Resolve one compatibility PlayerBuild to its canonical build identity.

    Exact Gamertag + character + build-name ownership is preferred.  A fallback
    without Gamertag is allowed only when it identifies exactly one canonical
    build, so ambiguous human-readable labels never silently pick a record.
    """
    character_name = str(getattr(build, "Name", "") or "").strip().casefold()
    gamertag = str(getattr(build, "Gamertag", "") or "").strip().casefold()
    build_name = str(getattr(build, "BuildName", "") or "").strip().casefold()

    catalog = catalog_service.load()
    exact: list[str] = []
    fallback: list[str] = []
    for record in catalog.get("builds", []):
        if not isinstance(record, dict):
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            payload = record.get("legacy") if isinstance(record.get("legacy"), dict) else {}
        record_character = str(payload.get("Name") or "").strip().casefold()
        record_gamertag = str(payload.get("Gamertag") or "").strip().casefold()
        record_build = str(record.get("name") or payload.get("BuildName") or "").strip().casefold()
        build_id = str(record.get("build_id") or "").strip()
        if not build_id or record_character != character_name or record_build != build_name:
            continue
        fallback.append(build_id)
        if record_gamertag == gamertag:
            exact.append(build_id)

    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    if len(fallback) == 1:
        return fallback[0]
    return None


class BuildRotationArtifactService:
    """Atomic JSON persistence for the latest completed rotation per build."""

    def __init__(self, path: Path):
        self.path = Path(path)

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "rotations": {}}

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty()
        if not isinstance(raw, dict):
            return self._empty()
        rotations = raw.get("rotations")
        if not isinstance(rotations, dict):
            rotations = {}
        return {
            "schema_version": SCHEMA_VERSION,
            "rotations": {
                str(build_id): copy.deepcopy(artifact)
                for build_id, artifact in rotations.items()
                if str(build_id).strip() and isinstance(artifact, dict)
            },
        }

    def save_rotation(self, *, build_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
        identity = str(build_id or "").strip()
        if not identity:
            raise ValueError("build_id is required to save a rotation artifact")
        if not isinstance(artifact, dict) or not artifact.get("actions"):
            raise ValueError("a completed rotation with actions is required")

        document = self.load()
        normalized = jsonable(copy.deepcopy(artifact))
        document["rotations"][identity] = normalized
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
        return copy.deepcopy(normalized)

    def get_rotation(self, build_id: str) -> dict[str, Any] | None:
        identity = str(build_id or "").strip()
        if not identity:
            return None
        artifact = self.load()["rotations"].get(identity)
        return copy.deepcopy(artifact) if isinstance(artifact, dict) else None

    def has_rotation(self, build_id: str) -> bool:
        artifact = self.get_rotation(build_id)
        return bool(artifact and artifact.get("actions"))

    def delete_rotation(self, build_id: str) -> bool:
        identity = str(build_id or "").strip()
        if not identity:
            return False
        document = self.load()
        if identity not in document["rotations"]:
            return False
        document["rotations"].pop(identity, None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(
            json.dumps(document, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
        return True


__all__ = [
    "BuildRotationArtifactService",
    "SCHEMA_VERSION",
    "jsonable",
    "resolve_canonical_build_id",
]
