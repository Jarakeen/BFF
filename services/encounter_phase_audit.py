from __future__ import annotations

"""Read-only audit of source-backed phase thresholds and transition evidence."""

from dataclasses import dataclass
import re

from services.encounter_service import EncounterService

_PERCENT = re.compile(r"^\s*(100|[1-9]?\d)\s*%\s*$")

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

def audit_encounter_phases(service: EncounterService) -> EncounterPhaseAudit:
    phases, transitions = [], []
    for encounter_id in service.encounter_ids():
        encounter = service.get(encounter_id)
        for phase in encounter.phases:
            match = _PERCENT.fullmatch(phase.threshold)
            phases.append(EncounterPhaseAuditRow(encounter_id, phase.phase_id, phase.label, phase.threshold, int(match.group(1)) if match else None, "parsed" if match else "unresolved"))
        for fact in encounter.evidence_facts:
            if fact.fact_type.casefold() == "transition":
                transitions.append(EncounterTransitionAuditRow(encounter_id, fact.fact_id, fact.fact_key, fact.status, fact.value_json))
    return EncounterPhaseAudit(tuple(phases), tuple(transitions))
