from __future__ import annotations

"""Construct reviewed pre-H1 runtime witnesses for equipped ordinary gear sets."""

from dataclasses import dataclass

from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    BLESSING_OF_HIGH_ISLE_CONDITION,
)


@dataclass(frozen=True)
class ExtremeActualHealGearPreconditionWitness:
    active_conditions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def condition_context(self) -> frozenset[str]:
        return frozenset(self.active_conditions)


class ExtremeActualHealGearPreconditionWitnessService:
    """Prove simple, deterministic setup events immediately before standing H1."""

    @staticmethod
    def resolve(
        build: PlayerBuild,
        *,
        active_bar: str = "front",
    ) -> ExtremeActualHealGearPreconditionWitness:
        counts = GearStatInputResolver.equipped_set_counts(build, active_bar=active_bar)
        active: list[str] = []
        evidence: list[str] = []

        if int(counts.get("Blessing of High Isle", 0)) >= 5:
            active.append(BLESSING_OF_HIGH_ISLE_CONDITION)
            evidence.append(
                "recently_healed_in_combat: standing H1 setup may receive one heal in combat "
                "within Blessing of High Isle's 5-second power window"
            )

        return ExtremeActualHealGearPreconditionWitness(
            active_conditions=tuple(active),
            evidence=tuple(evidence),
            unresolved=(),
        )


__all__ = [
    "ExtremeActualHealGearPreconditionWitness",
    "ExtremeActualHealGearPreconditionWitnessService",
]
