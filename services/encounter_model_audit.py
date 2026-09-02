from __future__ import annotations

"""Read-only audit of Phase 9 encounter-model domain coverage.

This audit measures what the domain service can state from structured source
fields and reconciled evidence. Zero counts are coverage gaps, not negative
claims about the live encounter.
"""

from dataclasses import dataclass

from services.encounter_service import EncounterService


@dataclass(frozen=True)
class EncounterModelAuditRow:
    encounter_id: str
    boss_actor_count: int
    mechanic_count: int
    phase_count: int
    requirement_count: int
    positioning_constraint_count: int
    temporal_evidence_count: int
    transition_fact_count: int
    target_constraint_count: int
    evidence_fact_count: int
    add_group_fact_count: int
    damage_window_fact_count: int


@dataclass(frozen=True)
class EncounterModelAudit:
    rows: tuple[EncounterModelAuditRow, ...]

    @property
    def encounter_count(self) -> int:
        return len(self.rows)

    @property
    def encounters_with_mechanics(self) -> int:
        return sum(row.mechanic_count > 0 for row in self.rows)

    @property
    def encounters_with_phases(self) -> int:
        return sum(row.phase_count > 0 for row in self.rows)

    @property
    def encounters_with_requirements(self) -> int:
        return sum(row.requirement_count > 0 for row in self.rows)

    @property
    def encounters_with_positioning_constraints(self) -> int:
        return sum(row.positioning_constraint_count > 0 for row in self.rows)

    @property
    def encounters_with_temporal_evidence(self) -> int:
        return sum(row.temporal_evidence_count > 0 for row in self.rows)

    @property
    def encounters_with_transition_evidence(self) -> int:
        return sum(row.transition_fact_count > 0 for row in self.rows)

    @property
    def encounters_with_target_constraints(self) -> int:
        return sum(row.target_constraint_count > 0 for row in self.rows)

    @property
    def encounters_with_evidence(self) -> int:
        return sum(row.evidence_fact_count > 0 for row in self.rows)

    @property
    def encounters_with_add_group_evidence(self) -> int:
        return sum(row.add_group_fact_count > 0 for row in self.rows)

    @property
    def encounters_with_damage_window_evidence(self) -> int:
        return sum(row.damage_window_fact_count > 0 for row in self.rows)


def audit_encounter_model(service: EncounterService) -> EncounterModelAudit:
    """Measure Phase 9 structured coverage without interpreting source prose."""
    rows = []
    for encounter_id in service.encounter_ids():
        encounter = service.get(encounter_id)
        rows.append(
            EncounterModelAuditRow(
                encounter_id=encounter_id,
                boss_actor_count=sum(actor.kind == "boss" for actor in encounter.actors),
                mechanic_count=len(encounter.mechanics),
                phase_count=len(encounter.phases),
                requirement_count=len(service.requirements(encounter_id)),
                positioning_constraint_count=len(service.positioning_constraints(encounter_id)),
                temporal_evidence_count=len(service.temporal_evidence(encounter_id)),
                transition_fact_count=len(service.evidence_facts(encounter_id, "transition")),
                target_constraint_count=len(service.target_constraints(encounter_id)),
                evidence_fact_count=len(service.evidence_facts(encounter_id)),
                add_group_fact_count=len(service.add_group_evidence(encounter_id)),
                damage_window_fact_count=len(service.damage_window_evidence(encounter_id)),
            )
        )
    return EncounterModelAudit(tuple(rows))
