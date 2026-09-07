from __future__ import annotations

from dataclasses import dataclass

from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.passive_math import (
    WARDEN_ADVANCED_SPECIES_CRIT_DAMAGE_PER_SLOTTED,
    WARDEN_FLOURISH_RECOVERY_PERCENT,
    WARDEN_FROZEN_ARMOR_RESISTANCE_PER_SLOTTED,
)


@dataclass(frozen=True)
class ExtremeSubclassLineContribution:
    skill_line_id: str
    objective_key: str
    flat: float = 0.0
    percent: float = 0.0
    additive_ratio: float = 0.0
    condition: str = ""


class ExtremeSubclassLineEffectService:
    """Reviewed line-level effects usable by legal subclass configurations.

    This service is deliberately narrow. It models only class-line stat effects
    whose values are already represented by verified BFF math elsewhere. It does
    not parse passive tooltip prose, infer unknown class mechanics, or claim that
    an unreviewed line contributes zero.

    Slot-scaled maxima assume the active bar may devote all six slots (five
    normal abilities plus one Ultimate) to the selected class line when that is
    legal and useful for the requested extreme objective.
    """

    _ACTIVE_BAR_SLOTS = 6
    _NIGHTBLADE_PRESSURE_POINTS_RATING_PER_SLOT = 438.0
    _SORCERER_EXPERT_MAGE_POWER_PER_SLOT = 108.0

    @classmethod
    def contributions_for_line(
        cls,
        skill_line_id: str,
    ) -> tuple[ExtremeSubclassLineContribution, ...]:
        line = str(skill_line_id or "").strip().casefold()
        if not line:
            return ()

        if line == "assassination":
            rating = cls._NIGHTBLADE_PRESSURE_POINTS_RATING_PER_SLOT * cls._ACTIVE_BAR_SLOTS
            ratio = GearStatInputResolver.critical_rating_to_ratio(rating)
            return (
                ExtremeSubclassLineContribution(
                    skill_line_id=line,
                    objective_key="weapon_critical",
                    additive_ratio=ratio,
                    condition="Maximum reviewed Pressure Points value with six Nightblade abilities represented on the active bar.",
                ),
                ExtremeSubclassLineContribution(
                    skill_line_id=line,
                    objective_key="spell_critical",
                    additive_ratio=ratio,
                    condition="Maximum reviewed Pressure Points value with six Nightblade abilities represented on the active bar.",
                ),
            )

        if line == "storm_calling":
            power = cls._SORCERER_EXPERT_MAGE_POWER_PER_SLOT * cls._ACTIVE_BAR_SLOTS
            return (
                ExtremeSubclassLineContribution(
                    skill_line_id=line,
                    objective_key="weapon_damage",
                    flat=power,
                    condition="Maximum reviewed Expert Mage value with six Sorcerer abilities represented on the active bar.",
                ),
                ExtremeSubclassLineContribution(
                    skill_line_id=line,
                    objective_key="spell_damage",
                    flat=power,
                    condition="Maximum reviewed Expert Mage value with six Sorcerer abilities represented on the active bar.",
                ),
            )

        if line == "animal_companions":
            crit_damage = (
                WARDEN_ADVANCED_SPECIES_CRIT_DAMAGE_PER_SLOTTED
                * cls._ACTIVE_BAR_SLOTS
            )
            return (
                ExtremeSubclassLineContribution(
                    skill_line_id=line,
                    objective_key="critical_damage",
                    additive_ratio=crit_damage,
                    condition="Maximum reviewed Advanced Species value with six Animal Companions abilities represented on the active bar.",
                ),
                ExtremeSubclassLineContribution(
                    skill_line_id=line,
                    objective_key="magicka_recovery",
                    percent=WARDEN_FLOURISH_RECOVERY_PERCENT,
                    condition="Reviewed Flourish value with at least one Animal Companions ability on the active bar.",
                ),
                ExtremeSubclassLineContribution(
                    skill_line_id=line,
                    objective_key="stamina_recovery",
                    percent=WARDEN_FLOURISH_RECOVERY_PERCENT,
                    condition="Reviewed Flourish value with at least one Animal Companions ability on the active bar.",
                ),
            )

        if line == "winters_embrace":
            resistance = (
                WARDEN_FROZEN_ARMOR_RESISTANCE_PER_SLOTTED
                * cls._ACTIVE_BAR_SLOTS
            )
            return (
                ExtremeSubclassLineContribution(
                    skill_line_id=line,
                    objective_key="physical_resistance",
                    flat=resistance,
                    condition="Maximum reviewed Frozen Armor value with six Winter's Embrace abilities represented on the active bar.",
                ),
                ExtremeSubclassLineContribution(
                    skill_line_id=line,
                    objective_key="spell_resistance",
                    flat=resistance,
                    condition="Maximum reviewed Frozen Armor value with six Winter's Embrace abilities represented on the active bar.",
                ),
            )

        return ()

    @classmethod
    def contribution_for_objective(
        cls,
        skill_line_id: str,
        objective_key: str,
    ) -> ExtremeSubclassLineContribution | None:
        target = str(objective_key or "").strip()
        if not target:
            return None
        return next(
            (
                row
                for row in cls.contributions_for_line(skill_line_id)
                if row.objective_key == target
            ),
            None,
        )

    @classmethod
    def reviewed_lines(cls) -> tuple[str, ...]:
        return (
            "animal_companions",
            "assassination",
            "storm_calling",
            "winters_embrace",
        )
