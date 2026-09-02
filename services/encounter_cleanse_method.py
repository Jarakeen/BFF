from __future__ import annotations

"""Explicit Phase 10 cleanse-method semantics.

A generic Phase 9 ``requires_cleanse`` flag says only that a mechanic requires
removal/cleansing behavior. This module resolves *how* the cleanse is performed
only from exact reconciled ``cleanse_method`` evidence facts. It never infers a
method from mechanic prose, skill names, or the existence of a cleanse-capable
player ability.
"""

from dataclasses import dataclass
from enum import Enum

from services.encounter_service import EncounterService


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

    @property
    def requires_player_build_capability(self) -> bool | None:
        if self.resolution != CleanseMethodResolution.RESOLVED or self.method is None:
            return None
        return self.method in {CleanseMethod.SELF_SKILL, CleanseMethod.GROUP_SKILL}


class EncounterCleanseMethodService:
    """Resolve cleanse method only from exact source-qualified evidence facts."""

    FACT_TYPE = "cleanse_method"

    def __init__(self, encounter_service: EncounterService) -> None:
        self._encounter_service = encounter_service

    def methods(self, encounter_id: str) -> tuple[EncounterCleanseMethod, ...]:
        facts = self._encounter_service.evidence_facts(encounter_id, fact_type=self.FACT_TYPE)
        rows: list[EncounterCleanseMethod] = []

        for fact in facts:
            if fact.status == "conflicting":
                rows.append(
                    EncounterCleanseMethod(
                        encounter_id=encounter_id,
                        mechanic_name=fact.fact_key,
                        method=None,
                        resolution=CleanseMethodResolution.CONFLICTING,
                        interaction="",
                        fact_id=fact.fact_id,
                        reconciliation_status=fact.status,
                        distinct_sources=fact.distinct_sources,
                    )
                )
                continue

            value = fact.value
            if not isinstance(value, dict):
                rows.append(
                    EncounterCleanseMethod(
                        encounter_id=encounter_id,
                        mechanic_name=fact.fact_key,
                        method=None,
                        resolution=CleanseMethodResolution.UNRESOLVED,
                        interaction="",
                        fact_id=fact.fact_id,
                        reconciliation_status=fact.status,
                        distinct_sources=fact.distinct_sources,
                    )
                )
                continue

            mechanic_name = str(value.get("mechanic_name") or fact.fact_key).strip()
            method_raw = str(value.get("method") or "").strip()
            interaction = str(value.get("interaction") or "").strip()
            try:
                method = CleanseMethod(method_raw)
            except ValueError:
                method = None

            rows.append(
                EncounterCleanseMethod(
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
                )
            )

        return tuple(rows)
