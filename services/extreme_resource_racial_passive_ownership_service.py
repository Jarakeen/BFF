from __future__ import annotations

"""Reconcile racial passives against canonical Phase 5 resource parsing.

This service does not duplicate racial tooltip math. It isolates one canonical
racial passive at its max rank, sets sibling racial passives to rank zero, and
asks ``RacialPassiveStatRepository`` to resolve the exact canonical tooltip.

A clean resolution can then prove one of two things for a requested max-resource
objective:

* the passive contributes that objective and is already owned by the canonical
  racial progression path; or
* the passive resolves only to other reviewed stat/boundary families and is
  therefore irrelevant to that specific max-resource objective.

Unmapped racial tooltips remain unresolved. The service never assigns zero merely
because the requested resource name is absent from raw text.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.character_progression import CharacterProgression
from minmax.racial_passive_stat_repository import RacialPassiveStatRepository
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


class ExtremeResourceRacialPassiveOwnershipStatus(str, Enum):
    CANONICALLY_ACCOUNTED = "canonically_accounted"
    PROVEN_IRRELEVANT = "proven_irrelevant"


@dataclass(frozen=True)
class ExtremeResourceRacialPassiveOwnership:
    skill_line: str
    passive_name: str
    status: ExtremeResourceRacialPassiveOwnershipStatus
    source: str
    resolved_stats: tuple[str, ...] = ()
    boundaries: tuple[str, ...] = ()


class ExtremeResourceRacialPassiveOwnershipService:
    """Resolve one racial passive against the canonical Phase 5 parser."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(self, repository: RacialPassiveStatRepository) -> None:
        self.repository = repository

    @staticmethod
    def _race_name(passive: ExtremePlayerSkillRecord) -> str:
        line = str(passive.skill_line or "").strip()
        suffix = " skills"
        if line.casefold().endswith(suffix):
            return line[: -len(suffix)].strip()
        return ""

    @staticmethod
    def _same_racial_line(
        passive: ExtremePlayerSkillRecord,
        candidate: ExtremePlayerSkillRecord,
    ) -> bool:
        return (
            candidate.domain is ExtremeSkillDomain.RACIAL
            and str(candidate.skill_line or "").strip().casefold()
            == str(passive.skill_line or "").strip().casefold()
        )

    def resolve(
        self,
        passive: ExtremePlayerSkillRecord,
        objective_key: str,
        passives: tuple[ExtremePlayerSkillRecord, ...],
    ) -> ExtremeResourceRacialPassiveOwnership | None:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource racial-passive objective: {objective_key!r}")
        if passive.domain is not ExtremeSkillDomain.RACIAL:
            return None

        race_name = self._race_name(passive)
        if not race_name:
            return None

        siblings = tuple(row for row in passives if self._same_racial_line(passive, row))
        if not siblings:
            return None

        ranks: dict[str, int] = {row.name: 0 for row in siblings}
        try:
            target_rank = int(passive.max_rank or 0)
        except (TypeError, ValueError):
            target_rank = 0
        if target_rank <= 0:
            return None
        ranks[passive.name] = target_rank

        resolution = self.repository.resolve(
            race_name,
            CharacterProgression(passive_ranks=ranks),
        )
        if resolution.unresolved:
            return None

        try:
            objective_value = float(resolution.stats.get(key, 0.0) or 0.0)
        except (TypeError, ValueError):
            return None

        status = (
            ExtremeResourceRacialPassiveOwnershipStatus.CANONICALLY_ACCOUNTED
            if objective_value != 0.0
            else ExtremeResourceRacialPassiveOwnershipStatus.PROVEN_IRRELEVANT
        )

        # A clean empty result is only proof when the canonical repository itself
        # supplied a reviewed boundary (for example a known non-combat passive).
        # Otherwise an empty resolution could simply mean the parser learned
        # nothing useful, so fail closed.
        resolved_stats = tuple(sorted(str(name) for name in resolution.stats))
        boundaries = tuple(str(value) for value in resolution.boundaries)
        if (
            status is ExtremeResourceRacialPassiveOwnershipStatus.PROVEN_IRRELEVANT
            and not resolved_stats
            and not boundaries
        ):
            return None

        return ExtremeResourceRacialPassiveOwnership(
            skill_line=str(passive.skill_line or "").strip(),
            passive_name=str(passive.name or "").strip(),
            status=status,
            source="RacialPassiveStatRepository",
            resolved_stats=resolved_stats,
            boundaries=boundaries,
        )
