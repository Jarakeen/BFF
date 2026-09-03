from __future__ import annotations

"""Deterministic read-only access to canonical encounter records."""

import json
import sqlite3
from dataclasses import dataclass, field, replace
from pathlib import Path

from services.encounter_projection import (
    EncounterDefinition,
    EncounterMechanic,
    load_encounter_definition,
)


class EncounterSourceError(ValueError):
    """The canonical encounter source or persistence layer is malformed or ambiguous."""


class EncounterNotFoundError(LookupError):
    """No canonical boss source exists for the exact requested encounter id."""


_REQUIREMENT_TYPES = frozenset({"movement", "positioning", "cleanse", "interrupt"})
_REQUIREMENT_SUBJECTS = frozenset({"player", "boss", "unknown"})


def _clean_name(value: object) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _requirement_subjects(
    payload: dict,
    *,
    encounter_id: str,
    fact_key: str,
) -> tuple[tuple[str, str], ...]:
    raw = payload.get("requirement_subjects")
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise EncounterSourceError(
            f"Canonical mechanic requirement_subjects must be an object for {encounter_id}:{fact_key}"
        )

    subjects: list[tuple[str, str]] = []
    for raw_requirement_type, raw_subject in raw.items():
        requirement_type = str(raw_requirement_type or "").strip().casefold()
        subject = str(raw_subject or "").strip().casefold()
        if requirement_type not in _REQUIREMENT_TYPES:
            raise EncounterSourceError(
                f"Unsupported canonical mechanic requirement subject key {requirement_type!r} "
                f"for {encounter_id}:{fact_key}"
            )
        if subject not in _REQUIREMENT_SUBJECTS:
            raise EncounterSourceError(
                f"Unsupported canonical mechanic requirement subject {subject!r} "
                f"for {encounter_id}:{fact_key}:{requirement_type}"
            )
        subjects.append((requirement_type, subject))
    return tuple(sorted(subjects))


def _canonical_mechanics(
    database_path: Path,
    encounter_id: str,
) -> tuple[EncounterMechanic, ...]:
    if not database_path.exists():
        raise EncounterSourceError(f"Canonical encounter database is missing: {database_path}")

    connection = sqlite3.connect(database_path)
    try:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='encounter_canonical_fact'"
        ).fetchone()
        if table is None:
            raise EncounterSourceError(
                f"Canonical encounter database has no encounter_canonical_fact table: {database_path}"
            )
        rows = connection.execute(
            """
            SELECT fact_key, payload_json, review_status
            FROM encounter_canonical_fact
            WHERE encounter_id=? AND fact_type='mechanic_detail'
            ORDER BY fact_key, id
            """,
            (encounter_id,),
        ).fetchall()
    finally:
        connection.close()

    mechanics: list[EncounterMechanic] = []
    seen_names: set[str] = set()
    for fact_key, payload_json, review_status in rows:
        try:
            payload = json.loads(str(payload_json or ""))
        except json.JSONDecodeError as exc:
            raise EncounterSourceError(
                f"Invalid canonical mechanic payload for {encounter_id}:{fact_key}"
            ) from exc
        if not isinstance(payload, dict):
            raise EncounterSourceError(
                f"Canonical mechanic payload is not an object for {encounter_id}:{fact_key}"
            )
        name = str(payload.get("name") or "").strip()
        if not name:
            raise EncounterSourceError(
                f"Canonical mechanic payload has no name for {encounter_id}:{fact_key}"
            )
        identity = _clean_name(name)
        if identity in seen_names:
            raise EncounterSourceError(
                f"Duplicate canonical mechanic name for {encounter_id}: {name!r}"
            )
        seen_names.add(identity)
        mechanics.append(
            EncounterMechanic(
                mechanic_id=f"{encounter_id}:canonical:{fact_key}",
                name=name,
                description=str(payload.get("description") or ""),
                interpretation_status=str(review_status or "reviewed"),
                mechanic_type=payload.get("mechanic_type"),
                damage_type=payload.get("damage_type"),
                target_count=payload.get("target_count"),
                requires_movement=payload.get("requires_movement"),
                requires_positioning=payload.get("requires_positioning"),
                requires_cleanse=payload.get("requires_cleanse"),
                persistent_hazard=payload.get("persistent_hazard"),
                failure_is_fatal=payload.get("failure_is_fatal"),
                interruptible=payload.get("interruptible"),
                requirement_subjects=_requirement_subjects(
                    payload,
                    encounter_id=encounter_id,
                    fact_key=str(fact_key),
                ),
            )
        )
    return tuple(mechanics)


def _overlay_canonical_mechanics(
    definition: EncounterDefinition,
    database_path: Path,
) -> EncounterDefinition:
    persisted = _canonical_mechanics(database_path, definition.encounter_id)
    persisted_by_name = {_clean_name(row.name): row for row in persisted}

    # Literal/source-classified mechanics remain usable. Raw inferred rows are
    # review candidates, not canonical truth, and therefore do not flow into
    # downstream evaluation unless a reviewed canonical fact exists for them.
    mechanics: list[EncounterMechanic] = []
    for row in definition.mechanics:
        identity = _clean_name(row.name)
        if identity in persisted_by_name:
            continue
        if str(row.interpretation_status or "").strip().casefold() == "inferred":
            continue
        mechanics.append(row)
    mechanics.extend(persisted)
    return replace(definition, mechanics=tuple(mechanics))


@dataclass(frozen=True)
class EncounterRepository:
    boss_root: Path
    evidence_root: Path
    database_path: Path | None = None
    _boss_paths: dict[str, Path] = field(init=False, repr=False, compare=False)
    _evidence_paths: dict[str, Path] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_boss_paths", self._index(self.boss_root, "id"))
        object.__setattr__(self, "_evidence_paths", self._index(self.evidence_root, "encounter_id"))

    @staticmethod
    def _index(root: Path, identity_key: str) -> dict[str, Path]:
        if not root.is_dir():
            raise EncounterSourceError(f"Canonical encounter directory is missing: {root}")
        indexed: dict[str, Path] = {}
        for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise EncounterSourceError(f"Invalid canonical encounter JSON: {path}") from exc
            identity = payload.get(identity_key) if isinstance(payload, dict) else None
            if not isinstance(identity, str) or not identity.strip():
                raise EncounterSourceError(f"Missing {identity_key!r} in canonical encounter JSON: {path}")
            if identity in indexed:
                raise EncounterSourceError(
                    f"Duplicate canonical encounter {identity_key} {identity!r}: {indexed[identity]} and {path}"
                )
            indexed[identity] = path
        return indexed

    @classmethod
    def from_data_root(cls, data_root: Path) -> "EncounterRepository":
        database_path = data_root / "eso.db"
        return cls(
            data_root / "eso_info" / "bosses",
            data_root / "encounter_evidence",
            database_path=database_path if database_path.exists() else None,
        )

    def encounter_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._boss_paths))

    def get(self, encounter_id: str) -> EncounterDefinition:
        if not isinstance(encounter_id, str) or not encounter_id:
            raise ValueError("encounter_id must be a non-empty canonical id")
        boss_path = self._boss_paths.get(encounter_id)
        if boss_path is None:
            raise EncounterNotFoundError(f"No canonical encounter source for id {encounter_id!r}")
        definition = load_encounter_definition(
            boss_path,
            evidence_packet_path=self._evidence_paths.get(encounter_id),
        )
        if self.database_path is None:
            return definition
        return _overlay_canonical_mechanics(definition, self.database_path)
