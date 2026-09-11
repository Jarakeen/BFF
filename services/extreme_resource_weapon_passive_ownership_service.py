from __future__ import annotations

"""Reviewed weapon-passive ownership for Extreme max-resource audits.

This is a proof/coverage service, not weapon math. It reuses canonical weapon
passive classification plus the reviewed Deadly Bash implementation boundary to
prove that selected weapon passives cannot alter Max Health, Max Magicka, or Max
Stamina. Current-resource restoration, healing, penetration, status chance, block
state, bash damage, and bash cost are intentionally distinct from maximum-resource
objectives.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.weapon_passive_classification import VERIFIED_WEAPON_PASSIVE_RULES
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


class ExtremeResourceWeaponPassiveOwnershipStatus(str, Enum):
    PROVEN_IRRELEVANT = "proven_irrelevant"


@dataclass(frozen=True)
class ExtremeResourceWeaponPassiveOwnership:
    skill_line: str
    passive_name: str
    status: ExtremeResourceWeaponPassiveOwnershipStatus
    source: str
    effect_family: str


class ExtremeResourceWeaponPassiveOwnershipService:
    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    @staticmethod
    def _normalized(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def _rows(cls) -> tuple[ExtremeResourceWeaponPassiveOwnership, ...]:
        rows = [
            ExtremeResourceWeaponPassiveOwnership(
                skill_line=rule.skill_line,
                passive_name=rule.passive,
                status=ExtremeResourceWeaponPassiveOwnershipStatus.PROVEN_IRRELEVANT,
                source="weapon_passive_classification.VERIFIED_WEAPON_PASSIVE_RULES",
                effect_family=f"{rule.layer.value}: {rule.reason}",
            )
            for rule in VERIFIED_WEAPON_PASSIVE_RULES
        ]
        rows.append(
            ExtremeResourceWeaponPassiveOwnership(
                skill_line="One Hand and Shield",
                passive_name="Deadly Bash",
                status=ExtremeResourceWeaponPassiveOwnershipStatus.PROVEN_IRRELEVANT,
                source="ExtremeDeadlyBashService",
                effect_family="bash damage and bash cost only",
            )
        )
        return tuple(rows)

    @classmethod
    def resolve(
        cls,
        passive: ExtremePlayerSkillRecord,
        objective_key: str,
    ) -> ExtremeResourceWeaponPassiveOwnership | None:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource weapon-passive objective: {objective_key!r}")
        if passive.domain is not ExtremeSkillDomain.WEAPON:
            return None

        target = (cls._normalized(passive.skill_line), cls._normalized(passive.name))
        for row in cls._rows():
            identity = (cls._normalized(row.skill_line), cls._normalized(row.passive_name))
            if identity == target:
                return row
        return None

    @classmethod
    def reviewed(cls) -> tuple[ExtremeResourceWeaponPassiveOwnership, ...]:
        return tuple(sorted(cls._rows(), key=lambda row: (row.skill_line.casefold(), row.passive_name.casefold())))
