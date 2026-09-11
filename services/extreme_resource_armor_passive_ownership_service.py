from __future__ import annotations

"""Reviewed ownership boundaries for armor passives in Extreme max-resource audits.

This service is a proof ledger, not a second mechanics engine. Rows are admitted
only when the shared armor resolver or a reviewed canonical Update-50 armor tooltip
makes the effect family explicit enough to determine whether it can modify Max
Health, Max Magicka, or Max Stamina.

Implemented shared-resolver passives retain their canonical ownership here. The
aggregate Light/Heavy Armor Bonuses and Penalties rows are also reviewed explicitly
because their complete U50 effect families contain mitigation, action-cost,
movement/stealth, block, bash, and crowd-control modifiers but no maximum-resource
modifier.
"""

from dataclasses import dataclass
from enum import Enum

from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


class ExtremeResourceArmorPassiveOwnershipStatus(str, Enum):
    CANONICALLY_ACCOUNTED = "canonically_accounted"
    PROVEN_IRRELEVANT = "proven_irrelevant"


@dataclass(frozen=True)
class ExtremeResourceArmorPassiveOwnership:
    skill_line: str
    passive_name: str
    source: str
    effect_family: str
    affected_objectives: tuple[str, ...] = ()

    @property
    def identity(self) -> tuple[str, str]:
        return (self.skill_line, self.passive_name)

    def status_for(self, objective_key: str) -> ExtremeResourceArmorPassiveOwnershipStatus:
        return (
            ExtremeResourceArmorPassiveOwnershipStatus.CANONICALLY_ACCOUNTED
            if objective_key in self.affected_objectives
            else ExtremeResourceArmorPassiveOwnershipStatus.PROVEN_IRRELEVANT
        )


class ExtremeResourceArmorPassiveOwnershipService:
    """Resolve exact reviewed armor-passive ownership for a max-resource audit."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    _ROWS = (
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Light Armor",
            passive_name="Light Armor Bonuses",
            source="Canonical Update-50 Light Armor tooltip review",
            effect_family="magical-damage mitigation, roll-dodge/break-free/bash cost, and sneak movement only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Light Armor",
            passive_name="Light Armor Penalties",
            source="Canonical Update-50 Light Armor tooltip review",
            effect_family="martial-damage taken, block cost, and bash damage only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Light Armor",
            passive_name="Evocation",
            source="ArmorPassiveInputResolver",
            effect_family="magicka recovery only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Light Armor",
            passive_name="Concentration",
            source="ArmorPassiveInputResolver",
            effect_family="physical/spell penetration only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Light Armor",
            passive_name="Spell Warding",
            source="ArmorPassiveInputResolver",
            effect_family="spell resistance only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Light Armor",
            passive_name="Prodigy",
            source="ArmorPassiveInputResolver",
            effect_family="weapon/spell critical only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Medium Armor",
            passive_name="Wind Walker",
            source="ArmorPassiveInputResolver",
            effect_family="stamina recovery only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Medium Armor",
            passive_name="Agility",
            source="ArmorPassiveInputResolver",
            effect_family="weapon/spell damage only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Medium Armor",
            passive_name="Dexterity",
            source="ArmorPassiveInputResolver",
            effect_family="critical damage/healing only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Heavy Armor",
            passive_name="Heavy Armor Bonuses",
            source="Canonical Update-50 Heavy Armor tooltip review",
            effect_family="martial-damage mitigation, block amount, bash damage, and crowd-control-immunity mitigation only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Heavy Armor",
            passive_name="Heavy Armor Penalties",
            source="Canonical Update-50 Heavy Armor tooltip review",
            effect_family="magical-damage taken, sprint movement, roll-dodge cost, and sneak detection only",
        ),
        ExtremeResourceArmorPassiveOwnership(
            skill_line="Heavy Armor",
            passive_name="Juggernaut",
            source="ArmorPassiveInputResolver",
            effect_family="max health only",
            affected_objectives=("max_health",),
        ),
    )

    @staticmethod
    def _normalized(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def resolve(
        cls,
        passive: ExtremePlayerSkillRecord,
        objective_key: str,
    ) -> tuple[ExtremeResourceArmorPassiveOwnership, ExtremeResourceArmorPassiveOwnershipStatus] | None:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource armor-passive objective: {objective_key!r}")
        if passive.domain is not ExtremeSkillDomain.ARMOR:
            return None

        target = (
            cls._normalized(passive.skill_line),
            cls._normalized(passive.name),
        )
        for row in cls._ROWS:
            identity = (
                cls._normalized(row.skill_line),
                cls._normalized(row.passive_name),
            )
            if identity == target:
                return row, row.status_for(key)
        return None

    @classmethod
    def reviewed(cls) -> tuple[ExtremeResourceArmorPassiveOwnership, ...]:
        return tuple(
            sorted(
                cls._ROWS,
                key=lambda row: (
                    row.skill_line.casefold(),
                    row.passive_name.casefold(),
                ),
            )
        )
