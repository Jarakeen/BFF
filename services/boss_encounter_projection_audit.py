from __future__ import annotations

"""Read-only coverage audit for projecting the tracked boss corpus into evidence."""

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from services.boss_encounter_projection import BossEncounterProjection, project_boss_file
from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_promotion import (
    PROMOTION_BLOCKED,
    PROMOTION_ELIGIBLE,
    PROMOTION_REVIEW_REQUIRED,
    build_encounter_promotion_preview,
)


@dataclass(frozen=True)
class BossProjectionFailure:
    path: Path
    reason: str


@dataclass(frozen=True)
class BossEncounterProjectionAudit:
    source_dir: Path
    source_files: int
    projected_bosses: int
    bosses_with_mechanics: int
    mechanics: int
    abilities: int
    phases: int
    inferred_mechanics: int
    incomplete_mechanics: int
    evidence_rows: int
    reconciled_facts: int
    promotion_eligible: int
    review_required: int
    blocked: int
    database_encounters_matched: int
    database_encounters_missing: tuple[str, ...]
    failures: tuple[BossProjectionFailure, ...]


def _encounter_ids(connection: sqlite3.Connection | None) -> set[str] | None:
    if connection is None:
        return None
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='encounter'"
    ).fetchone()
    if table is None:
        return set()
    return {str(row[0]) for row in connection.execute("SELECT id FROM encounter")}


def audit_boss_encounter_projection(
    source_dir: Path,
    *,
    connection: sqlite3.Connection | None = None,
) -> BossEncounterProjectionAudit:
    source_dir = Path(source_dir)
    paths = tuple(sorted(source_dir.glob("*.json"))) if source_dir.exists() else ()
    projections: list[BossEncounterProjection] = []
    failures: list[BossProjectionFailure] = []

    for path in paths:
        try:
            projections.append(project_boss_file(path))
        except (OSError, ValueError, TypeError) as exc:
            failures.append(BossProjectionFailure(path=path, reason=str(exc)))

    evidence_rows = [row for projection in projections for row in projection.evidence]
    facts = reconcile_encounter_evidence(evidence_rows)
    candidates = build_encounter_promotion_preview(facts)

    eligible = sum(candidate.promotion_status == PROMOTION_ELIGIBLE for candidate in candidates)
    review = sum(candidate.promotion_status == PROMOTION_REVIEW_REQUIRED for candidate in candidates)
    blocked = sum(candidate.promotion_status == PROMOTION_BLOCKED for candidate in candidates)

    database_ids = _encounter_ids(connection)
    if database_ids is None:
        matched = 0
        missing: tuple[str, ...] = ()
    else:
        projected_ids = {projection.encounter_id for projection in projections}
        matched = len(projected_ids & database_ids)
        missing = tuple(sorted(projected_ids - database_ids))

    return BossEncounterProjectionAudit(
        source_dir=source_dir,
        source_files=len(paths),
        projected_bosses=len(projections),
        bosses_with_mechanics=sum(projection.mechanic_count > 0 for projection in projections),
        mechanics=sum(projection.mechanic_count for projection in projections),
        abilities=sum(projection.ability_count for projection in projections),
        phases=sum(projection.phase_count for projection in projections),
        inferred_mechanics=sum(projection.inferred_mechanic_count for projection in projections),
        incomplete_mechanics=sum(projection.incomplete_mechanic_count for projection in projections),
        evidence_rows=len(evidence_rows),
        reconciled_facts=len(facts),
        promotion_eligible=eligible,
        review_required=review,
        blocked=blocked,
        database_encounters_matched=matched,
        database_encounters_missing=missing,
        failures=tuple(failures),
    )
