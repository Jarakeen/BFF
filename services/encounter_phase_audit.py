from __future__ import annotations

"""Read-only audit of source-backed phase thresholds and transition evidence."""

from dataclasses import dataclass

from services.encounter_service import EncounterService


@dataclass(frozen=True)
class EncounterPhaseAuditRow:
    encounter_id: str
    phase_id: str
    label: str
    raw_threshold: str
    threshold_percent: int | None
    resolution: str


@dataclass(frozen=True)
class EncounterTransitionAuditRow:
    encounter_id: str
    fact_id: str
    fact_key: str
    status: str
    value_json: str | None


@dataclass(frozen=True)
class EncounterPhaseAudit:
    phases: tuple[EncounterPhaseAuditRow, ...]
    transitions: tuple[EncounterTransitionAuditRow, ...]

    @property
    def parsed_phase_count(self) -> int:
        return sum(row.resolution == "parsed" for row in self.phases)

    @property
    def unresolved_phase_count(self) -> int:
        return sum(row.resolution == "unresolved" for row in self.phases)

    @property
    def corroborated_transition_count(self) -> int:
        return sum(row.status == "corroborated" for row in self.transitions)

    @property
    def conflicting_transition_count(self) -> int:
        return sum(row.status == "conflicting" for row in self.transitions)


def audit_encounter_phases(service: EncounterService) -> EncounterPhaseAudit:
    phases = []
    transitions = []
    for encounter_id in service.encounter_ids():
        encounter = service.get(encounter_id)
        for phase in encounter.phases:
            threshold = service.phase_threshold(encounter_id, phase.phase_id)
            phases.append(
                EncounterPhaseAuditRow(
                    encounter_id=encounter_id,
                    phase_id=phase.phase_id,
                    label=phase.label,
                    raw_threshold=threshold.raw_value,
                    threshold_percent=threshold.percent,
                    resolution=threshold.resolution,
                )
            )
        for fact in encounter.evidence_facts:
            if fact.fact_type.casefold() == "transition":
                transitions.append(
                    EncounterTransitionAuditRow(
                        encounter_id=encounter_id,
                        fact_id=fact.fact_id,
                        fact_key=fact.fact_key,
                        status=fact.status,
                        value_json=fact.value_json,
                    )
                )
    return EncounterPhaseAudit(tuple(phases), tuple(transitions))
