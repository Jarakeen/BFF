from __future__ import annotations

"""Persist completed Rotation Builder plans as build-owned user artifacts.

Rotation artifacts are user state, not ESO reference data, so they live beside
builds.json rather than in eso.db. Records are keyed by the canonical build_id;
character names and build names are display metadata only.
"""

import copy
import json
import os
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.user_artifact_pydantic_schema import validate_rotation_artifact_document

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


def rotation_plan_from_artifact(artifact: dict[str, Any]) -> RotationPlan:
    """Restore one saved artifact into the canonical immutable RotationPlan.

    Saved artifacts are not repaired or reinterpreted here. Every required plan and
    action field must still satisfy the canonical RotationPlan contract. Invalid or
    stale artifacts fail closed instead of being massaged into executable evidence.
    """
    if not isinstance(artifact, dict):
        raise ValueError("rotation artifact must be an object")
    raw_actions = artifact.get("actions")
    if not isinstance(raw_actions, list) or not raw_actions:
        raise ValueError("rotation artifact requires saved actions")

    actions: list[RotationAction] = []
    for index, raw in enumerate(raw_actions):
        if not isinstance(raw, dict):
            raise ValueError(f"rotation artifact action {index} must be an object")
        try:
            actions.append(
                RotationAction(
                    time_seconds=raw.get("time_seconds"),
                    sequence=int(raw.get("sequence")),
                    kind=RotationActionKind(str(raw.get("kind") or "")),
                    name=raw.get("name"),
                    bar=raw.get("bar"),
                )
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"rotation artifact action {index} is invalid: {exc}"
            ) from exc

    try:
        return RotationPlan(
            character_name=str(artifact.get("character_name") or "").strip(),
            build_name=str(artifact.get("build_name") or "").strip(),
            duration_seconds=artifact.get("duration_seconds"),
            actions=tuple(actions),
            assumptions=tuple(artifact.get("assumptions") or ()),
            unresolved=tuple(artifact.get("unresolved") or ()),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"saved rotation artifact is not a valid RotationPlan: {exc}") from exc


def resolve_canonical_build_id(catalog_service, build) -> str | None:
    """Resolve one compatibility PlayerBuild to its canonical build identity.

    An explicit BuildId is authoritative. Human-readable ownership fields are
    migration fallback only for compatibility rows that genuinely lack a stable id.
    A stale explicit id fails closed rather than silently rebinding the build to
    another record that happens to share its labels.
    """
    catalog = catalog_service.load_strict()
    explicit_build_id = str(getattr(build, "BuildId", "") or "").strip()
    if explicit_build_id:
        matches = [
            str(record.get("build_id") or "").strip()
            for record in catalog.get("builds", [])
            if isinstance(record, dict)
            and str(record.get("build_id") or "").strip() == explicit_build_id
        ]
        return explicit_build_id if len(matches) == 1 else None

    character_name = str(getattr(build, "Name", "") or "").strip().casefold()
    gamertag = str(getattr(build, "Gamertag", "") or "").strip().casefold()
    build_name = str(getattr(build, "BuildName", "") or "").strip().casefold()

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
            return validate_rotation_artifact_document(raw)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(f"Rotation artifacts failed to load safely: {exc}") from exc

    def _write_document(self, document: dict[str, Any]) -> None:
        validated = validate_rotation_artifact_document(document)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", suffix=".tmp", delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                json.dump(validated, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        read_back = validate_rotation_artifact_document(
            json.loads(self.path.read_text(encoding="utf-8"))
        )
        if read_back != validated:
            raise RuntimeError("Rotation artifacts did not round-trip exactly")

    def save_rotation(self, *, build_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
        identity = str(build_id or "").strip()
        if not identity:
            raise ValueError("build_id is required to save a rotation artifact")
        if not isinstance(artifact, dict) or not artifact.get("actions"):
            raise ValueError("a completed rotation with actions is required")

        document = self.load()
        normalized = jsonable(copy.deepcopy(artifact))
        document["rotations"][identity] = normalized
        self._write_document(document)
        return copy.deepcopy(normalized)

    def get_rotation(self, build_id: str) -> dict[str, Any] | None:
        identity = str(build_id or "").strip()
        if not identity:
            return None
        artifact = self.load()["rotations"].get(identity)
        return copy.deepcopy(artifact) if isinstance(artifact, dict) else None

    def get_rotation_plan(self, build_id: str) -> RotationPlan | None:
        """Return the exact saved RotationPlan for one canonical build identity."""
        artifact = self.get_rotation(build_id)
        if artifact is None:
            return None
        return rotation_plan_from_artifact(artifact)

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
        self._write_document(document)
        return True


__all__ = [
    "BuildRotationArtifactService",
    "SCHEMA_VERSION",
    "jsonable",
    "resolve_canonical_build_id",
    "rotation_plan_from_artifact",
]
