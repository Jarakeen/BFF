from __future__ import annotations

"""Explicit Phase 10 interrupt-method semantics.

A generic Phase 9 ``interruptible`` flag says only that a mechanic can be
interrupted. This module resolves *how* the interrupt is performed only from
exact reconciled ``interrupt_method`` evidence. It never assumes that bash,
a ranged skill, or an encounter interaction works merely because a source says
"interruptible".
"""

from dataclasses import dataclass
from enum import Enum

from services.encounter_service import EncounterService


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

    @property
    def requires_player_build_capability(self) -> bool | None:
        if self.resolution != InterruptMethodResolution.RESOLVED or self.method is None:
            return None
        return self.method == InterruptMethod.PLAYER_SKILL


class EncounterInterruptMethodService:
    """Resolve interrupt method only from exact source-qualified evidence facts."""

    FACT_TYPE = "interrupt_method"

    def __init__(self, encounter_service: EncounterService) -> None:
        self._encounter_service = encounter_service

    def methods(self, encounter_id: str) -> tuple[EncounterInterruptMethod, ...]:
        rows: list[EncounterInterruptMethod] = []
        for fact in self._encounter_service.evidence_facts(
            encounter_id,
            fact_type=self.FACT_TYPE,
        ):
            if fact.status == "conflicting":
                rows.append(
                    EncounterInterruptMethod(
                        encounter_id=encounter_id,
                        mechanic_name=fact.fact_key,
                        method=None,
                        resolution=InterruptMethodResolution.CONFLICTING,
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
                    EncounterInterruptMethod(
                        encounter_id=encounter_id,
                        mechanic_name=fact.fact_key,
                        method=None,
                        resolution=InterruptMethodResolution.UNRESOLVED,
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
            ranged_raw = value.get("ranged_required")
            ranged_required = ranged_raw if isinstance(ranged_raw, bool) else None
            try:
                method = InterruptMethod(method_raw)
            except ValueError:
                method = None

            rows.append(
                EncounterInterruptMethod(
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
            )

        return tuple(rows)
