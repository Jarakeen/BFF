from __future__ import annotations

"""Source-backed Phase 10 movement/positioning handling semantics.

Generic ``requires_movement`` / ``requires_positioning`` flags say only that the
mechanic demands player execution. This module resolves a coarse handling method
from explicit structured ``execution_method`` evidence. It never derives strategy
from prose and never invents coordinates, assignments, or raid choreography.
"""

from dataclasses import dataclass
from enum import Enum

from services.encounter_service import EncounterEvidenceFact, EncounterService


class ExecutionMethod(str, Enum):
    DODGE = "dodge"
    BAIT_FARTHEST = "bait_farthest"
    AVOID_HAZARD = "avoid_hazard"
    MOVE_TO_INTERACTION = "move_to_interaction"
    HAZARD_DROP_MANAGEMENT = "hazard_drop_management"
    SEPARATE_ADD_FROM_BOSS = "separate_add_from_boss"


class ExecutionMethodResolution(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class EncounterExecutionMethod:
    encounter_id: str
    mechanic_name: str
    requirement_type: str
    method: ExecutionMethod | None
    resolution: ExecutionMethodResolution
    interaction: str
    fact_id: str
    reconciliation_status: str
    distinct_sources: int


class EncounterExecutionMethodService:
    """Resolve movement/positioning methods from exact structured evidence."""

    FACT_TYPE = "execution_method"

    def __init__(self, encounter_service: EncounterService) -> None:
        self._encounter_service = encounter_service

    @staticmethod
    def _row(encounter_id: str, fact: EncounterEvidenceFact) -> EncounterExecutionMethod:
        if fact.status == "conflicting":
            return EncounterExecutionMethod(
                encounter_id=encounter_id,
                mechanic_name=fact.fact_key,
                requirement_type="",
                method=None,
                resolution=ExecutionMethodResolution.CONFLICTING,
                interaction="",
                fact_id=fact.fact_id,
                reconciliation_status=fact.status,
                distinct_sources=fact.distinct_sources,
            )

        value = fact.value
        if not isinstance(value, dict):
            return EncounterExecutionMethod(
                encounter_id=encounter_id,
                mechanic_name=fact.fact_key,
                requirement_type="",
                method=None,
                resolution=ExecutionMethodResolution.UNRESOLVED,
                interaction="",
                fact_id=fact.fact_id,
                reconciliation_status=fact.status,
                distinct_sources=fact.distinct_sources,
            )

        mechanic_name = str(value.get("mechanic_name") or fact.fact_key).strip()
        requirement_type = str(value.get("requirement_type") or "").strip().casefold()
        interaction = str(value.get("interaction") or "").strip()
        method_raw = str(value.get("method") or "").strip()
        try:
            method = ExecutionMethod(method_raw)
        except ValueError:
            method = None

        valid_requirement = requirement_type in {"movement", "positioning"}
        resolved = method is not None and valid_requirement
        return EncounterExecutionMethod(
            encounter_id=encounter_id,
            mechanic_name=mechanic_name,
            requirement_type=requirement_type,
            method=method,
            resolution=(
                ExecutionMethodResolution.RESOLVED
                if resolved
                else ExecutionMethodResolution.UNRESOLVED
            ),
            interaction=interaction,
            fact_id=fact.fact_id,
            reconciliation_status=fact.status,
            distinct_sources=fact.distinct_sources,
        )

    def methods(self, encounter_id: str) -> tuple[EncounterExecutionMethod, ...]:
        return tuple(
            self._row(encounter_id, fact)
            for fact in self._encounter_service.evidence_facts(
                encounter_id,
                fact_type=self.FACT_TYPE,
            )
        )
