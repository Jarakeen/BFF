from __future__ import annotations

"""Read-only coverage audit for structured encounter requirement fields."""

from dataclasses import dataclass

from services.encounter_service import EncounterService


@dataclass(frozen=True)
class EncounterRequirementAuditRow:
    encounter_id: str
    mechanic_id: str
    mechanic_name: str
    interpretation_status: str
    movement: bool | None
    positioning: bool | None
    cleanse: bool | None
    interruptible: bool | None
    target_count: int | None

    @property
    def explicit_requirement_count(self) -> int:
        return sum(
            value is True
            for value in (
                self.movement,
                self.positioning,
                self.cleanse,
                self.interruptible,
            )
        )

    @property
    def unresolved_requirement_field_count(self) -> int:
        return sum(
            value is None
            for value in (
                self.movement,
                self.positioning,
                self.cleanse,
                self.interruptible,
            )
        )


@dataclass(frozen=True)
class EncounterRequirementAudit:
    rows: tuple[EncounterRequirementAuditRow, ...]

    @property
    def mechanic_count(self) -> int:
        return len(self.rows)

    @property
    def mechanics_with_requirements(self) -> int:
        return sum(row.explicit_requirement_count > 0 for row in self.rows)

    @property
    def mechanics_with_unresolved_requirement_fields(self) -> int:
        return sum(row.unresolved_requirement_field_count > 0 for row in self.rows)

    @property
    def explicit_requirement_count(self) -> int:
        return sum(row.explicit_requirement_count for row in self.rows)


def audit_encounter_requirements(service: EncounterService) -> EncounterRequirementAudit:
    """Report structured coverage without interpreting mechanic prose."""
    rows = []
    for encounter_id in service.encounter_ids():
        encounter = service.get(encounter_id)
        for mechanic in encounter.mechanics:
            rows.append(
                EncounterRequirementAuditRow(
                    encounter_id=encounter_id,
                    mechanic_id=mechanic.mechanic_id,
                    mechanic_name=mechanic.name,
                    interpretation_status=mechanic.interpretation_status,
                    movement=mechanic.requires_movement,
                    positioning=mechanic.requires_positioning,
                    cleanse=mechanic.requires_cleanse,
                    interruptible=mechanic.interruptible,
                    target_count=mechanic.target_count,
                )
            )
    return EncounterRequirementAudit(tuple(rows))
