from __future__ import annotations

"""Explicit Phase 10 interrupt-method semantics.

Encounter-specific ``interrupt_method`` evidence has priority. When a Phase 9
mechanic is explicitly structured as interruptible but has no encounter-specific
method evidence, the sourced ESO-wide standard-interrupt rule supplies the core
bash method. This avoids copying one universal combat rule into every encounter
packet while still allowing explicit encounter exceptions to override it.
"""

from dataclasses import dataclass
from enum import Enum

from services.encounter_service import EncounterService
from services.eso_combat_rules import STANDARD_INTERRUPT


class InterruptMethod(str, Enum):
    CORE_BASH = "core_bash"
    PLAYER_SKILL = "player_skill"
    ENCOUNTER_INTERACTION = "encounter_interaction"
    UNINTERRUPTIBLE = "uninterruptible"


class InterruptMethodResolution(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class EncounterInterruptMethod:
    encounter_id: str
    mechanic_name: str
    method: InterruptMethod | None
    resolution: InterruptMethodResolution
    interaction: str
    fact_id: str
    reconciliation_status: str
    distinct_sources: int
    ranged_required: bool | None = None
    rule_source_name: str = ""
    rule_source_url: str = ""

    @property
    def requires_player_build_capability(self) -> bool | None:
        if self.resolution != InterruptMethodResolution.RESOLVED or self.method is None:
            return None
        return self.method == InterruptMethod.PLAYER_SKILL


class EncounterInterruptMethodService:
    """Resolve interrupt methods with encounter evidence overriding global rules."""

    FACT_TYPE = "interrupt_method"

    def __init__(self, encounter_service: EncounterService) -> None:
        self._encounter_service = encounter_service

    @staticmethod
    def _explicit_row(encounter_id: str, fact) -> EncounterInterruptMethod:
        if fact.status == "conflicting":
            return EncounterInterruptMethod(
                encounter_id=encounter_id,
                mechanic_name=fact.fact_key,
                method=None,
                resolution=InterruptMethodResolution.CONFLICTING,
                interaction="",
                fact_id=fact.fact_id,
                reconciliation_status=fact.status,
                distinct_sources=fact.distinct_sources,
            )

        value = fact.value
        if not isinstance(value, dict):
            return EncounterInterruptMethod(
                encounter_id=encounter_id,
                mechanic_name=fact.fact_key,
                method=None,
                resolution=InterruptMethodResolution.UNRESOLVED,
                interaction="",
                fact_id=fact.fact_id,
                reconciliation_status=fact.status,
                distinct_sources=fact.distinct_sources,
            )

        mechanic_name = str(value.get("mechanic_name") or fact.fact_key).strip()
        method_raw = str(value.get("method") or "").strip()
        interaction = str(value.get("interaction") or "").strip()
        ranged_raw = value.get("ranged_required")
        ranged_required = ranged_raw if isinstance(ranged_raw, bool) else None
        try:
            method = InterruptMethod(method_raw)
        except ValueError:
            method = None

        return EncounterInterruptMethod(
            encounter_id=encounter_id,
            mechanic_name=mechanic_name,
            method=method,
            resolution=(
                InterruptMethodResolution.RESOLVED
                if method is not None
                else InterruptMethodResolution.UNRESOLVED
            ),
            interaction=interaction,
            fact_id=fact.fact_id,
            reconciliation_status=fact.status,
            distinct_sources=fact.distinct_sources,
            ranged_required=ranged_required,
        )

    @staticmethod
    def _global_bash_row(encounter_id: str, mechanic_name: str) -> EncounterInterruptMethod:
        return EncounterInterruptMethod(
            encounter_id=encounter_id,
            mechanic_name=mechanic_name,
            method=InterruptMethod.CORE_BASH,
            resolution=InterruptMethodResolution.RESOLVED,
            interaction="standard_interrupt_bash",
            fact_id=f"global_rule:{STANDARD_INTERRUPT.rule_id}",
            reconciliation_status="global_rule",
            distinct_sources=1,
            ranged_required=False,
            rule_source_name=STANDARD_INTERRUPT.source_name,
            rule_source_url=STANDARD_INTERRUPT.source_url,
        )

    def methods(self, encounter_id: str) -> tuple[EncounterInterruptMethod, ...]:
        explicit = tuple(
            self._explicit_row(encounter_id, fact)
            for fact in self._encounter_service.evidence_facts(
                encounter_id,
                fact_type=self.FACT_TYPE,
            )
        )

        # Encounter-specific method evidence is authoritative for this layer.
        # This includes unresolved or conflicting evidence: uncertainty must not
        # be overwritten by a generic ESO-wide fallback. Until explicit facts
        # can be matched safely to individual mechanics, the conservative rule
        # is to suppress the fallback for the encounter whenever such evidence
        # exists.
        if explicit:
            return explicit

        return tuple(
            self._global_bash_row(encounter_id, requirement.mechanic_name)
            for requirement in self._encounter_service.requirements(encounter_id)
            if requirement.requirement_type == "interrupt"
        )
