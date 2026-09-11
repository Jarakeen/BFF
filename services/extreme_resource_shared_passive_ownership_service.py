from __future__ import annotations

"""Reviewed shared-resolver ownership for non-class max-resource passives.

This is a proof ledger, not a second mechanics implementation. Rows are admitted
only when an existing canonical shared resolver makes the passive's effect family
explicit enough to prove whether it can alter Max Health, Max Magicka, or Max
Stamina.
"""

from dataclasses import dataclass
from enum import Enum

from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)

_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


class ExtremeResourceSharedPassiveOwnershipStatus(str, Enum):
    PROVEN_IRRELEVANT = "proven_irrelevant"


@dataclass(frozen=True)
class ExtremeResourceSharedPassiveOwnership:
    domain: ExtremeSkillDomain
    skill_line: str
    passive_name: str
    status: ExtremeResourceSharedPassiveOwnershipStatus
    source: str
    effect_family: str


class ExtremeResourceSharedPassiveOwnershipService:
    """Resolve exact reviewed guild/alliance/weapon passive ownership."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    _ROWS = (
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.GUILD,
            skill_line="Fighters Guild",
            passive_name="Slayer",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="GuildPassiveInputResolver",
            effect_family="weapon/spell damage only",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.ALLIANCE_WAR,
            skill_line="Support",
            passive_name="Magicka Aid",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="AllianceSupportPassiveInputResolver",
            effect_family="magicka recovery only",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.WEAPON,
            skill_line="One Hand and Shield",
            passive_name="Fortress",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="OneHandShieldPassiveInputResolver",
            effect_family="block cost only",
        ),
        ExtremeResourceSharedPassiveOwnership(
            domain=ExtremeSkillDomain.WEAPON,
            skill_line="One Hand and Shield",
            passive_name="Deflect Bolts",
            status=ExtremeResourceSharedPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="OneHandShieldPassiveInputResolver",
            effect_family="block mitigation only",
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
    ) -> ExtremeResourceSharedPassiveOwnership | None:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme shared-passive objective: {objective_key!r}")

        target = (
            passive.domain,
            cls._normalized(passive.skill_line),
            cls._normalized(passive.name),
        )
        for row in cls._ROWS:
            identity = (
                row.domain,
                cls._normalized(row.skill_line),
                cls._normalized(row.passive_name),
            )
            if identity == target:
                return row
        return None

    @classmethod
    def reviewed(cls) -> tuple[ExtremeResourceSharedPassiveOwnership, ...]:
        return tuple(
            sorted(
                cls._ROWS,
                key=lambda row: (
                    row.domain.value,
                    row.skill_line.casefold(),
                    row.passive_name.casefold(),
                ),
            )
        )
