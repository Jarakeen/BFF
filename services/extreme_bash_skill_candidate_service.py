from __future__ import annotations

"""Classify legal active skills whose damage is explicitly Bash-classified.

This service deliberately keeps Bash-classified active abilities separate from
ESO's standard Bash event.  Power Bash and its morphs have their own ability
coefficients/costs even though their damage is considered Bash damage, so they
must never be injected into the standard ``BashDamage`` formula as a flat or
multiplicative source.
"""

from dataclasses import dataclass
import re

from .extreme_player_skill_candidate_service import (
    ExtremePlayerSkillCandidateService,
    ExtremePlayerSkillLegalityContext,
)
from .extreme_skill_universe_service import ExtremePlayerSkillRecord


_BASH_CLASSIFICATION = re.compile(
    r"\b(?:this ability(?:'s)?|the ability(?:'s)?) damage is considered Bash damage\b",
    re.IGNORECASE,
)
_POWER_SLAM_COST = re.compile(
    r"reduces the cost of your next (?P<skill>.+?) cast within "
    r"(?P<duration>\d+(?:\.\d+)?) seconds by (?P<percent>\d+(?:\.\d+)?)%",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtremeBashSkillCandidate:
    skill_id: int
    ability_id: int
    name: str
    skill_line: str
    description: str
    bash_classified: bool = True
    standard_bash_formula_channel: bool = False
    conditional_cost_reduction: float | None = None
    conditional_cost_window_seconds: float | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved


class ExtremeBashSkillCandidateService:
    """Return legal Bash-classified active abilities without conflating events."""

    def __init__(self, candidate_service: ExtremePlayerSkillCandidateService) -> None:
        self.candidate_service = candidate_service

    @staticmethod
    def _is_bash_classified(row: ExtremePlayerSkillRecord) -> bool:
        return bool(_BASH_CLASSIFICATION.search(str(row.description or "")))

    @staticmethod
    def _project(row: ExtremePlayerSkillRecord) -> ExtremeBashSkillCandidate:
        description = str(row.description or "").strip()
        unresolved: list[str] = []
        conditional_cost_reduction: float | None = None
        conditional_cost_window_seconds: float | None = None

        cost_match = _POWER_SLAM_COST.search(description)
        if cost_match:
            conditional_cost_reduction = -float(cost_match.group("percent")) / 100.0
            conditional_cost_window_seconds = float(cost_match.group("duration"))

        if row.max_rank_ability_id is None:
            unresolved.append(f"{row.name}: canonical max-rank ability id unavailable")
            ability_id = 0
        else:
            ability_id = int(row.max_rank_ability_id)

        return ExtremeBashSkillCandidate(
            skill_id=int(row.skill_id),
            ability_id=ability_id,
            name=row.name,
            skill_line=row.skill_line,
            description=description,
            conditional_cost_reduction=conditional_cost_reduction,
            conditional_cost_window_seconds=conditional_cost_window_seconds,
            unresolved=tuple(unresolved),
        )

    def candidates(
        self,
        context: ExtremePlayerSkillLegalityContext,
    ) -> tuple[ExtremeBashSkillCandidate, ...]:
        rows = self.candidate_service.candidates(context, ultimate=False)
        return tuple(
            self._project(row)
            for row in rows
            if self._is_bash_classified(row)
        )
