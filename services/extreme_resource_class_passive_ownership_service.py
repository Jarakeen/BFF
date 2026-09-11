from __future__ import annotations

"""Reviewed ownership boundaries for class passives in Extreme max-resource audits.

This service is deliberately not a passive calculator. It records exact class
passives whose shared canonical resolver already defines their effect family well
enough to prove whether they can alter Max Health, Max Magicka, or Max Stamina.

Rows are conservative and explicit. A passive is never treated as irrelevant just
because its tooltip fails to mention the requested resource; the owning canonical
resolver must prove the effect family. Additional class families can be added as
their shared resolvers are reviewed.
"""

from dataclasses import dataclass
from enum import Enum

from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


class ExtremeResourceClassPassiveOwnershipStatus(str, Enum):
    CANONICALLY_ACCOUNTED = "canonically_accounted"
    PROVEN_IRRELEVANT = "proven_irrelevant"


@dataclass(frozen=True)
class ExtremeResourceClassPassiveOwnership:
    skill_line: str
    passive_name: str
    status: ExtremeResourceClassPassiveOwnershipStatus
    source: str
    effect_family: str

    @property
    def identity(self) -> tuple[str, str]:
        return (self.skill_line, self.passive_name)


class ExtremeResourceClassPassiveOwnershipService:
    """Resolve reviewed shared-resolver ownership for one class passive."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    # WardenPassiveInputResolver is explicit about all three of these mechanics:
    # Flourish -> Magicka/Stamina Recovery, Advanced Species -> Critical Damage,
    # Frozen Armor -> Physical/Spell Resistance. None can modify a max-resource
    # objective, although all depend on legal class-line/bar ownership.
    _ROWS = (
        ExtremeResourceClassPassiveOwnership(
            skill_line="Animal Companions",
            passive_name="Flourish",
            status=ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="WardenPassiveInputResolver",
            effect_family="magicka/stamina recovery only",
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Animal Companions",
            passive_name="Advanced Species",
            status=ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="WardenPassiveInputResolver",
            effect_family="critical damage only",
        ),
        ExtremeResourceClassPassiveOwnership(
            skill_line="Winter's Embrace",
            passive_name="Frozen Armor",
            status=ExtremeResourceClassPassiveOwnershipStatus.PROVEN_IRRELEVANT,
            source="WardenPassiveInputResolver",
            effect_family="physical/spell resistance only",
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
    ) -> ExtremeResourceClassPassiveOwnership | None:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource class-passive objective: {objective_key!r}")
        if passive.domain is not ExtremeSkillDomain.CLASS:
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
                return row
        return None

    @classmethod
    def reviewed(cls) -> tuple[ExtremeResourceClassPassiveOwnership, ...]:
        return tuple(
            sorted(
                cls._ROWS,
                key=lambda row: (
                    row.skill_line.casefold(),
                    row.passive_name.casefold(),
                ),
            )
        )
