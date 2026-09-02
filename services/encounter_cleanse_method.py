from __future__ import annotations

"""Explicit Phase 10 cleanse-method semantics.

A generic Phase 9 ``requires_cleanse`` flag says only that a mechanic requires
removal/cleansing behavior. This module resolves *how* the cleanse is performed
from source-qualified structured evidence only. It never infers a method from
mechanic prose, skill names, or the existence of a cleanse-capable player ability.

Preferred evidence is an exact ``cleanse_method`` fact. The current corpus also
contains an older structured ``requires_cleanse_pool`` boolean; that exact field is
accepted as a conservative encounter-interaction signal without asserting that
ordinary player cleanse skills do or do not work.
"""

from dataclasses import dataclass
from enum import Enum

from services.encounter_service import EncounterEvidenceFact, EncounterService


class CleanseMethod(str, Enum):
    SELF_SKILL = "self_skill"
    GROUP_SKILL = "group_skill"
    ENCOUNTER_INTERACTION = "encounter_interaction"
    UNCLEANSABLE = "uncleansable"


class CleanseMethodResolution(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class EncounterCleanseMethod:
    encounter_id: str
    mechanic_name: str
    method: CleanseMethod | None
    resolution: CleanseMethodResolution
    interaction: str
    fact_id: str
    reconciliation_status: str
    distinct_sources: int
    player_skill_effectiveness_known: bool = False

    @property
    def requires_player_build_capability(self) -> bool | None:
        if self.resolution != CleanseMethodResolution.RESOLVED or self.method is None:
            return None
        return self.method in {CleanseMethod.SELF_SKILL, CleanseMethod.GROUP_SKILL}


class EncounterCleanseMethodService:
    """Resolve cleanse method only from exact source-qualified structured facts."""

    FACT_TYPE = "cleanse_method"
    LEGACY_FACT_TYPE = "mechanic_detail"
    LEGACY_POOL_FIELD = "requires_cleanse_pool"

    def __init__(self, encounter_service: EncounterService) -> None:
        self._encounter_service = encounter_service

    @staticmethod
    def _explicit_fact(encounter_id: str, fact: EncounterEvidenceFact) -> EncounterCleanseMethod:
        if fact.status == "conflicting":
            return EncounterCleanseMethod(
                encounter_id=encounter_id,
                mechanic_name=fact.fact_key,
                method=None,
                resolution=CleanseMethodResolution.CONFLICTING,
                interaction="",
                fact_id=fact.fact_id,
                reconciliation_status=fact.status,
                distinct_sources=fact.distinct_sources,
            )

        value = fact.value
        if not isinstance(value, dict):
            return EncounterCleanseMethod(
                encounter_id=encounter_id,
                mechanic_name=fact.fact_key,
                method=None,
                resolution=CleanseMethodResolution.UNRESOLVED,
                interaction="",
                fact_id=fact.fact_id,
                reconciliation_status=fact.status,
                distinct_sources=fact.distinct_sources,
            )

        mechanic_name = str(value.get("mechanic_name") or fact.fact_key).strip()
        method_raw = str(value.get("method") or "").strip()
        interaction = str(value.get("interaction") or "").strip()
        effectiveness_known = value.get("player_skill_effectiveness_known") is True
        try:
            method = CleanseMethod(method_raw)
        except ValueError:
            method = None

        return EncounterCleanseMethod(
            encounter_id=encounter_id,
            mechanic_name=mechanic_name,
            method=method,
            resolution=(
                CleanseMethodResolution.RESOLVED
                if method is not None
                else CleanseMethodResolution.UNRESOLVED
            ),
            interaction=interaction,
            fact_id=fact.fact_id,
            reconciliation_status=fact.status,
            distinct_sources=fact.distinct_sources,
            player_skill_effectiveness_known=effectiveness_known,
        )

    @classmethod
    def _legacy_pool_fact(
        cls,
        encounter_id: str,
        fact: EncounterEvidenceFact,
    ) -> EncounterCleanseMethod | None:
        if fact.status == "conflicting":
            return None
        value = fact.value
        if not isinstance(value, dict) or value.get(cls.LEGACY_POOL_FIELD) is not True:
            return None
        return EncounterCleanseMethod(
            encounter_id=encounter_id,
            mechanic_name=fact.fact_key,
            method=CleanseMethod.ENCOUNTER_INTERACTION,
            resolution=CleanseMethodResolution.RESOLVED,
            interaction="cleanse_pool",
            fact_id=fact.fact_id,
            reconciliation_status=fact.status,
            distinct_sources=fact.distinct_sources,
            player_skill_effectiveness_known=False,
        )

    def methods(self, encounter_id: str) -> tuple[EncounterCleanseMethod, ...]:
        explicit = self._encounter_service.evidence_facts(encounter_id, fact_type=self.FACT_TYPE)
        if explicit:
            return tuple(self._explicit_fact(encounter_id, fact) for fact in explicit)

        rows: list[EncounterCleanseMethod] = []
        for fact in self._encounter_service.evidence_facts(
            encounter_id,
            fact_type=self.LEGACY_FACT_TYPE,
        ):
            row = self._legacy_pool_fact(encounter_id, fact)
            if row is not None:
                rows.append(row)
        return tuple(rows)
