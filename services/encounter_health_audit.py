from __future__ import annotations

"""Read-only health-source coverage audit for the canonical encounter corpus."""

from dataclasses import dataclass

from services.encounter_service import EncounterService

DIFFICULTIES = ("normal", "veteran", "hardmode")

@dataclass(frozen=True)
class EncounterHealthAuditRow:
    encounter_id: str
    difficulty: str
    raw_value: str
    value: int | None
    annotation: str
    resolution: str

@dataclass(frozen=True)
class EncounterHealthAudit:
    rows: tuple[EncounterHealthAuditRow, ...]

    @property
    def parsed_count(self) -> int:
        return sum(row.resolution == "parsed" for row in self.rows)

    @property
    def unresolved_count(self) -> int:
        return sum(row.resolution == "unresolved" for row in self.rows)

    @property
    def missing_count(self) -> int:
        return sum(not row.raw_value for row in self.rows)

def audit_encounter_health(service: EncounterService) -> EncounterHealthAudit:
    rows = []
    for encounter_id in service.encounter_ids():
        for difficulty in DIFFICULTIES:
            health = service.health(encounter_id, difficulty)
            rows.append(EncounterHealthAuditRow(encounter_id, difficulty, health.raw_value, health.value, health.annotation, health.resolution))
    return EncounterHealthAudit(tuple(rows))
