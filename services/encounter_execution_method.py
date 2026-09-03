from __future__ import annotations

"""Source-backed Phase 10 movement/positioning handling semantics.

Generic ``requires_movement`` / ``requires_positioning`` flags say only that the
mechanic demands player execution. This module resolves a coarse handling method
from explicit structured evidence only. It never derives strategy from prose and
never invents coordinates, assignments, or raid choreography.

Preferred evidence is an exact ``execution_method`` fact. The current corpus also
contains older reconciled mechanic facts with explicit booleans such as
``avoidable_by_dodge`` and ``persistent_hazard``. Those exact fields are accepted
through narrowly scoped mappings, analogous to the cleanse-method legacy pool
bridge.
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
    def _build(
        encounter_id: str,
        fact: EncounterEvidenceFact,
        *,
        mechanic_name: str,
        requirement_type: str,
        method: ExecutionMethod | None,
        interaction: str = "",
    ) -> EncounterExecutionMethod:
        return EncounterExecutionMethod(
            encounter_id=encounter_id,
            mechanic_name=mechanic_name,
            requirement_type=requirement_type,
            method=method,
            resolution=(
                ExecutionMethodResolution.CONFLICTING
                if fact.status == "conflicting"
                else ExecutionMethodResolution.RESOLVED
                if method is not None and requirement_type in {"movement", "positioning"}
                else ExecutionMethodResolution.UNRESOLVED
            ),
            interaction=interaction,
            fact_id=fact.fact_id,
            reconciliation_status=fact.status,
            distinct_sources=fact.distinct_sources,
        )

    @classmethod
    def _explicit_fact(
        cls,
        encounter_id: str,
        fact: EncounterEvidenceFact,
    ) -> EncounterExecutionMethod:
        value = fact.value
        if fact.status == "conflicting" or not isinstance(value, dict):
            return cls._build(
                encounter_id,
                fact,
                mechanic_name=fact.fact_key,
                requirement_type="",
                method=None,
            )

        mechanic_name = str(value.get("mechanic_name") or fact.fact_key).strip()
        requirement_type = str(value.get("requirement_type") or "").strip().casefold()
        interaction = str(value.get("interaction") or "").strip()
        method_raw = str(value.get("method") or "").strip()
        try:
            method = ExecutionMethod(method_raw)
        except ValueError:
            method = None
        return cls._build(
            encounter_id,
            fact,
            mechanic_name=mechanic_name,
            requirement_type=requirement_type,
            method=method,
            interaction=interaction,
        )

    @classmethod
    def _legacy_rows(
        cls,
        encounter_id: str,
        fact: EncounterEvidenceFact,
    ) -> tuple[EncounterExecutionMethod, ...]:
        if fact.status == "conflicting":
            return ()
        value = fact.value

        if fact.fact_key == "savage_blitz_targeting" and isinstance(value, dict):
            rows: list[EncounterExecutionMethod] = []
            if value.get("avoidable_by_dodge") is True:
                rows.append(
                    cls._build(
                        encounter_id,
                        fact,
                        mechanic_name="Savage Blitz",
                        requirement_type="movement",
                        method=ExecutionMethod.DODGE,
                    )
                )
            if value.get("targets_farthest_player") is True:
                rows.append(
                    cls._build(
                        encounter_id,
                        fact,
                        mechanic_name="Savage Blitz",
                        requirement_type="positioning",
                        method=ExecutionMethod.BAIT_FARTHEST,
                    )
                )
            return tuple(rows)

        if fact.fact_key == "blistering_smash_core_behavior" and isinstance(value, dict):
            if value.get("persistent_hazard") is True:
                return (
                    cls._build(
                        encounter_id,
                        fact,
                        mechanic_name="Blistering Smash",
                        requirement_type="positioning",
                        method=ExecutionMethod.AVOID_HAZARD,
                    ),
                )

        if fact.fact_key == "noxious_sludge_core_behavior" and isinstance(value, dict):
            rows = []
            if value.get("requires_cleanse_pool") is True:
                rows.append(
                    cls._build(
                        encounter_id,
                        fact,
                        mechanic_name="Noxious Sludge",
                        requirement_type="movement",
                        method=ExecutionMethod.MOVE_TO_INTERACTION,
                        interaction="cleanse_pool",
                    )
                )
            if value.get("uncleansed_targets_drop_poison_aoe") is True:
                rows.append(
                    cls._build(
                        encounter_id,
                        fact,
                        mechanic_name="Noxious Sludge",
                        requirement_type="positioning",
                        method=ExecutionMethod.HAZARD_DROP_MANAGEMENT,
                        interaction="noxious_pool",
                    )
                )
            return tuple(rows)

        if fact.fact_key == "proximity_enrage_exists" and value is True:
            return (
                cls._build(
                    encounter_id,
                    fact,
                    mechanic_name="Summon Havocrel Annihilators",
                    requirement_type="positioning",
                    method=ExecutionMethod.SEPARATE_ADD_FROM_BOSS,
                ),
            )

        return ()

    def methods(self, encounter_id: str) -> tuple[EncounterExecutionMethod, ...]:
        explicit = self._encounter_service.evidence_facts(encounter_id, fact_type=self.FACT_TYPE)
        if explicit:
            return tuple(self._explicit_fact(encounter_id, fact) for fact in explicit)

        rows: list[EncounterExecutionMethod] = []
        for fact_type in ("mechanic_detail", "mechanic_state"):
            for fact in self._encounter_service.evidence_facts(encounter_id, fact_type=fact_type):
                rows.extend(self._legacy_rows(encounter_id, fact))
        return tuple(rows)
