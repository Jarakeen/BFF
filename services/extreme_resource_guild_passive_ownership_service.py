from __future__ import annotations

"""Reviewed ownership boundaries for guild passives in Extreme max-resource audits.

This service does not duplicate guild passive math. It records exact guild passives
whose shared canonical resolver already defines their max-resource ownership well
enough for the coverage audit to distinguish a real contributor from an objective-
specific non-contributor.
"""

from dataclasses import dataclass
from enum import Enum

from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)

_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


class ExtremeResourceGuildPassiveOwnershipStatus(str, Enum):
    CANONICALLY_ACCOUNTED = "canonically_accounted"
    PROVEN_IRRELEVANT = "proven_irrelevant"


@dataclass(frozen=True)
class ExtremeResourceGuildPassiveOwnership:
    skill_line: str
    passive_name: str
    source: str
    effect_family: str
    affected_objectives: tuple[str, ...] = ()

    def status_for(self, objective_key: str) -> ExtremeResourceGuildPassiveOwnershipStatus:
        return (
            ExtremeResourceGuildPassiveOwnershipStatus.CANONICALLY_ACCOUNTED
            if objective_key in self.affected_objectives
            else ExtremeResourceGuildPassiveOwnershipStatus.PROVEN_IRRELEVANT
        )


class ExtremeResourceGuildPassiveOwnershipService:
    """Resolve reviewed guild-passive ownership for one max-resource objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    _ROWS = (
        ExtremeResourceGuildPassiveOwnership(
            skill_line="Mages Guild",
            passive_name="Magicka Controller",
            source="GuildPassiveInputResolver",
            effect_family="active-bar Max Magicka and Magicka Recovery percentage only",
            affected_objectives=("max_magicka",),
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
    ) -> tuple[
        ExtremeResourceGuildPassiveOwnership,
        ExtremeResourceGuildPassiveOwnershipStatus,
    ] | None:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource guild-passive objective: {objective_key!r}")
        if passive.domain is not ExtremeSkillDomain.GUILD:
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
    def reviewed(cls) -> tuple[ExtremeResourceGuildPassiveOwnership, ...]:
        return cls._ROWS
