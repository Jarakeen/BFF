from __future__ import annotations

"""Construct reviewed H1 setup/runtime witnesses for equipped ordinary gear sets."""

from dataclasses import dataclass

from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION,
    BLESSING_OF_HIGH_ISLE_CONDITION,
    TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION,
)


FLEDGLINGS_NEST_MINOR_COURAGE_CONDITION = "fledglings_nest_minor_courage_active"
PHOENIX_MOTH_MINOR_COURAGE_CONDITION = "phoenix_moth_minor_courage_active"
SPELL_POWER_CURE_MAJOR_COURAGE_CONDITION = "spell_power_cure_major_courage_active"
VESTMENT_OF_OLORIME_MAJOR_COURAGE_CONDITION = "vestment_of_olorime_major_courage_active"


@dataclass(frozen=True)
class ExtremeActualHealGearPreconditionWitness:
    active_conditions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def condition_context(self) -> frozenset[str]:
        return frozenset(self.active_conditions)


class ExtremeActualHealGearPreconditionWitnessService:
    """Prove deterministic setup events and scenario-owned states for standing H1."""

    @staticmethod
    def resolve(
        build: PlayerBuild,
        *,
        active_bar: str = "front",
    ) -> ExtremeActualHealGearPreconditionWitness:
        counts = GearStatInputResolver.equipped_set_counts(build, active_bar=active_bar)
        active: list[str] = []
        evidence: list[str] = []

        if int(counts.get("Ancient Dragonguard", 0)) >= 5:
            active.append(ANCIENT_DRAGONGUARD_ABOVE_HALF_HEALTH_CONDITION)
            evidence.append(
                "wearer_health_above_50_percent: standing H1 scenario may snapshot the caster "
                "above 50% current Health, activating Ancient Dragonguard's power branch"
            )

        if int(counts.get("Titanborn Strength", 0)) >= 5:
            active.append(TITANBORN_STRENGTH_BELOW_HALF_HEALTH_CONDITION)
            evidence.append(
                "wearer_in_combat_below_50_percent_health: standing H1 scenario may snapshot "
                "the caster in combat below 50% current Health, activating Titanborn Strength's "
                "quadrupled five-piece power branch"
            )

        if int(counts.get("Blessing of High Isle", 0)) >= 5:
            active.append(BLESSING_OF_HIGH_ISLE_CONDITION)
            evidence.append(
                "recently_healed_in_combat: standing H1 setup may receive one heal in combat "
                "within Blessing of High Isle's 5-second power window"
            )

        if int(counts.get("Fledgling's Nest", 0)) >= 5:
            active.append(FLEDGLINGS_NEST_MINOR_COURAGE_CONDITION)
            evidence.append(
                "fledglings_nest_minor_courage_active: standing H1 setup may cast one "
                "ground-effect ability in combat, create the Gryphon Nest, leave it once, "
                "and snapshot the heal inside the resulting 10-second Minor Courage window"
            )

        if int(counts.get("Phoenix Moth Theurge", 0)) >= 5:
            active.append(PHOENIX_MOTH_MINOR_COURAGE_CONDITION)
            evidence.append(
                "phoenix_moth_minor_courage_active: standing H1 setup may perform one prior "
                "self-heal and snapshot the target heal inside Phoenix Moth Theurge's "
                "10-second Minor Courage window"
            )

        if int(counts.get("Spell Power Cure", 0)) >= 5:
            active.append(SPELL_POWER_CURE_MAJOR_COURAGE_CONDITION)
            evidence.append(
                "spell_power_cure_major_courage_active: standing H1 setup may perform one "
                "prior self-overheal and snapshot the target heal inside Spell Power Cure's "
                "5-second Major Courage window"
            )

        if int(counts.get("Vestment of Olorime", 0)) >= 5:
            active.append(VESTMENT_OF_OLORIME_MAJOR_COURAGE_CONDITION)
            evidence.append(
                "vestment_of_olorime_major_courage_active: standing H1 setup may cast one "
                "ground-effect ability in combat, create the Circle of Might, stand in it, "
                "and snapshot the heal inside the resulting 20-second Major Courage window"
            )

        return ExtremeActualHealGearPreconditionWitness(
            active_conditions=tuple(active),
            evidence=tuple(evidence),
            unresolved=(),
        )


__all__ = [
    "FLEDGLINGS_NEST_MINOR_COURAGE_CONDITION",
    "PHOENIX_MOTH_MINOR_COURAGE_CONDITION",
    "SPELL_POWER_CURE_MAJOR_COURAGE_CONDITION",
    "VESTMENT_OF_OLORIME_MAJOR_COURAGE_CONDITION",
    "ExtremeActualHealGearPreconditionWitness",
    "ExtremeActualHealGearPreconditionWitnessService",
]
