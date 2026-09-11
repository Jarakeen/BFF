from __future__ import annotations

"""Reviewed ownership boundaries for armor passives in Extreme max-resource audits.

This service is a proof ledger, not a second mechanics engine. Each row is backed by
``ArmorPassiveInputResolver`` and records the exact resource objectives that the
shared canonical resolver can modify. For other max-resource objectives, the
passive is therefore proven irrelevant rather than left as contextual debt.

Only passives explicitly implemented by the shared resolver belong here. Armor
bonuses/penalties and unimplemented armor passives remain outside this ledger until
their complete mechanic families are reviewed.
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
    """Resolve exact shared armor-resolver ownership for a max-resource audit."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    _ROWS = (
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
