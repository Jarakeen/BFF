from __future__ import annotations

"""Immutable, source-backed encounter projections.

This module is deliberately a *reader* for the canonical UESP corpus and the
separate encounter-evidence packets.  It does not write SQLite data, interpret
strategy, select targets, or fabricate timing/geometry from prose.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from services.encounter_evidence import EncounterEvidence, reconcile_encounter_evidence


@dataclass(frozen=True)
class EncounterSource:
    url: str
    page_title: str
    revision_id: str
    retrieved_at: str
    license: str


@dataclass(frozen=True)
class EncounterActor:
    """An explicitly identified encounter actor, not a live target selection."""

    actor_id: str
    name: str
    kind: str
    species: str


@dataclass(frozen=True)
class EncounterMechanic:
    mechanic_id: str
    name: str
    description: str
    interpretation_status: str
    mechanic_type: str | None
    damage_type: str | None
    target_count: int | None
    requires_movement: bool | None
    requires_positioning: bool | None
    requires_cleanse: bool | None
    persistent_hazard: bool | None
    failure_is_fatal: bool | None
    interruptible: bool | None


@dataclass(frozen=True)
class EncounterPhase:
    phase_id: str
    label: str
    threshold: str
    description: str


@dataclass(frozen=True)
class EncounterEvidenceFact:
    """A reconciled evidence fact without a hidden conflict-resolution policy."""

    fact_id: str
    fact_type: str
    fact_key: str
    status: str
    value_json: str | None
    distinct_sources: int
    distinct_values: int
    evidence: tuple[EncounterSource, ...]

    @property
    def value(self) -> Any | None:
        """Return a fresh decoded value; the stored encounter contract remains immutable."""
        return json.loads(self.value_json) if self.value_json is not None else None


@dataclass(frozen=True)
class EncounterDefinition:
    """The smallest Phase 9 encounter truth consumable by later phases.

    ``phases`` and ``evidence_facts`` may be empty.  Empty means no structured,
    source-supported record exists yet; it never means that a phase or mechanic
    does not exist in the live encounter.
    """

    encounter_id: str
    content_id: str
    name: str
    difficulty_health: tuple[tuple[str, str], ...]
    source: EncounterSource
    actors: tuple[EncounterActor, ...]
    mechanics: tuple[EncounterMechanic, ...]
    phases: tuple[EncounterPhase, ...]
    evidence_facts: tuple[EncounterEvidenceFact, ...]


def _source_from(payload: dict[str, Any]) -> EncounterSource:
    source = payload.get("source") or {}
    return EncounterSource(
        url=str(source.get("url") or ""),
        page_title=str(source.get("page_title") or ""),
        revision_id=str(source.get("revision_id") or ""),
        retrieved_at=str(source.get("retrieved_at") or ""),
        license=str(source.get("license") or ""),
    )


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source_file:
        payload = json.load(source_file)
    if not isinstance(payload, dict):
        raise ValueError(f"Encounter source must be a JSON object: {path}")
    return payload


def _evidence_from_packet(packet_path: Path, encounter_id: str) -> tuple[EncounterEvidenceFact, ...]:
    if not packet_path.exists():
        return ()

    packet = _read_json(packet_path)
    packet_encounter_id = str(packet.get("encounter_id") or "").strip()
    if packet_encounter_id != encounter_id:
        raise ValueError(
            f"Evidence packet encounter_id {packet_encounter_id!r} does not match {encounter_id!r}"
        )

    rows = []
    for item in packet.get("evidence", []):
        if not isinstance(item, dict):
            raise ValueError(f"Evidence row in {packet_path} must be an object")
        rows.append(
            EncounterEvidence(
                encounter_id=encounter_id,
                fact_type=str(item.get("fact_type") or ""),
                fact_key=str(item.get("fact_key") or ""),
                value=item.get("value"),
                source_type=str(item.get("source_type") or ""),
                source_name=str(item.get("source_name") or ""),
                source_locator=str(item.get("source_locator") or ""),
                source_revision=str(item.get("source_revision") or ""),
                source_family=str(item.get("source_family") or ""),
                game_update=str(item.get("game_update") or ""),
                patch_version=str(item.get("patch_version") or ""),
                confidence=str(item.get("confidence") or "medium"),
                notes=str(item.get("notes") or ""),
            )
        )

    facts = []
    for fact in reconcile_encounter_evidence(rows):
        evidence = tuple(
            EncounterSource(
                url=row.source_locator,
                page_title=row.source_name,
                revision_id=row.source_revision,
                retrieved_at="",
                license="",
            )
            for row in fact.evidence
        )
        facts.append(
            EncounterEvidenceFact(
                fact_id=f"{encounter_id}:{fact.fact_type}:{fact.fact_key}",
                fact_type=fact.fact_type,
                fact_key=fact.fact_key,
                status=fact.status,
                value_json=(json.dumps(fact.value, ensure_ascii=False, sort_keys=True) if fact.value is not None else None),
                distinct_sources=fact.distinct_sources,
                distinct_values=fact.distinct_values,
                evidence=evidence,
            )
        )
    return tuple(facts)


def load_encounter_definition(
    boss_path: Path,
    *,
    evidence_packet_path: Path | None = None,
) -> EncounterDefinition:
    """Project one raw boss record without modifying source or database state."""
    payload = _read_json(boss_path)
    encounter_id = str(payload.get("id") or "").strip()
    if not encounter_id:
        raise ValueError(f"Encounter source has no id: {boss_path}")

    mechanics = tuple(
        EncounterMechanic(
            mechanic_id=f"{encounter_id}:mechanic:{index}",
            name=str(row.get("name") or ""),
            description=str(row.get("description") or ""),
            interpretation_status=str(row.get("interpretation_status") or "source"),
            mechanic_type=row.get("mechanic_type"),
            damage_type=row.get("damage_type"),
            target_count=row.get("target_count"),
            requires_movement=row.get("requires_movement"),
            requires_positioning=row.get("requires_positioning"),
            requires_cleanse=row.get("requires_cleanse"),
            persistent_hazard=row.get("persistent_hazard"),
            failure_is_fatal=row.get("failure_is_fatal"),
            interruptible=row.get("interruptible"),
        )
        for index, row in enumerate(payload.get("mechanics", ()), start=1)
        if isinstance(row, dict)
    )
    phases = tuple(
        EncounterPhase(
            phase_id=f"{encounter_id}:phase:{index}",
            label=str(row.get("label") or ""),
            threshold=str(row.get("threshold") or ""),
            description=str(row.get("description") or ""),
        )
        for index, row in enumerate(payload.get("phases", ()), start=1)
        if isinstance(row, dict)
    )
    health = payload.get("health") or {}
    difficulty_health = tuple(
        (difficulty, str(health.get(difficulty) or ""))
        for difficulty in ("normal", "veteran", "hardmode")
        if health.get(difficulty)
    )

    return EncounterDefinition(
        encounter_id=encounter_id,
        content_id=str(payload.get("content_id") or ""),
        name=str(payload.get("name") or encounter_id),
        difficulty_health=difficulty_health,
        source=_source_from(payload),
        actors=(
            EncounterActor(
                actor_id=encounter_id,
                name=str(payload.get("name") or encounter_id),
                kind="boss",
                species=str(payload.get("species") or ""),
            ),
        ),
        mechanics=mechanics,
        phases=phases,
        evidence_facts=_evidence_from_packet(evidence_packet_path, encounter_id) if evidence_packet_path else (),
    )
