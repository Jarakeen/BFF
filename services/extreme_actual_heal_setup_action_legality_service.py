from __future__ import annotations

"""Legal setup-action witnesses for Extreme H1 gear conditions.

This bridge deliberately reuses :class:`ExtremePlayerSkillCandidateService` for
route/bar legality.  It does not decide whether a gear set is valuable and it does
not mutate a build.  It answers one narrower question: does the selected legality
context contain a canonical active skill whose reviewed tooltip evidence proves a
requested setup capability?

Only exact reviewed capability families belong here.  Unknown prose fails closed.
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Protocol

from minmax.eso_markup import normalize_eso_markup
from services.extreme_player_skill_candidate_service import (
    ExtremePlayerSkillCandidateService,
    ExtremePlayerSkillLegalityContext,
)
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord


GRANTS_RESOLVE = "grants_resolve"


class _CandidateProvider(Protocol):
    def candidates(
        self,
        context: ExtremePlayerSkillLegalityContext,
        *,
        ultimate: bool | None = None,
    ) -> tuple[ExtremePlayerSkillRecord, ...]: ...


@dataclass(frozen=True)
class ExtremeActualHealSetupActionWitness:
    capability: str
    skill_name: str | None = None
    skill_line: str | None = None
    ability_id: int | None = None
    evidence: str | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def proven(self) -> bool:
        return bool(self.skill_name and not self.unresolved)


class ExtremeActualHealSetupActionLegalityService:
    """Find deterministic, route-legal setup actions for reviewed H1 capabilities."""

    _RESOLVE_PATTERNS = (
        re.compile(r"\b(?:gain|grant(?:s|ing)?(?: you| yourself)?)\s+(?:Major|Minor) Resolve\b", re.IGNORECASE),
        re.compile(r"\bgrants?\s+(?:you|yourself)\s+(?:Major|Minor) Resolve\b", re.IGNORECASE),
    )

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        candidate_service: _CandidateProvider | None = None,
    ) -> None:
        if database_path is None and candidate_service is None:
            raise ValueError("database_path or candidate_service is required")
        self.candidate_service = candidate_service or ExtremePlayerSkillCandidateService(
            database_path  # type: ignore[arg-type]
        )

    @staticmethod
    def _text(row: ExtremePlayerSkillRecord) -> str:
        normalized = normalize_eso_markup(str(row.description or "")).text
        return " ".join(normalized.split())

    @classmethod
    def _supports(cls, row: ExtremePlayerSkillRecord, capability: str) -> bool:
        text = cls._text(row)
        if capability == GRANTS_RESOLVE:
            return any(pattern.search(text) for pattern in cls._RESOLVE_PATTERNS)
        return False

    def witness(
        self,
        capability: str,
        context: ExtremePlayerSkillLegalityContext,
    ) -> ExtremeActualHealSetupActionWitness:
        key = str(capability or "").strip().casefold()
        if key != GRANTS_RESOLVE:
            return ExtremeActualHealSetupActionWitness(
                capability=key,
                unresolved=(f"unsupported H1 setup capability: {key or '<empty>'}",),
            )

        legal = self.candidate_service.candidates(context, ultimate=False)
        matches = tuple(row for row in legal if self._supports(row, key))
        if not matches:
            return ExtremeActualHealSetupActionWitness(
                capability=key,
                unresolved=(
                    f"{key} has no reviewed route-legal non-Ultimate active-skill witness",
                ),
            )

        witness = sorted(
            matches,
            key=lambda row: (
                row.domain.value,
                row.skill_line.casefold(),
                row.name.casefold(),
                row.max_rank_ability_id or 0,
            ),
        )[0]
        ability_id = witness.max_rank_ability_id or witness.base_ability_id or witness.skill_id
        return ExtremeActualHealSetupActionWitness(
            capability=key,
            skill_name=witness.name,
            skill_line=witness.skill_line,
            ability_id=int(ability_id) if ability_id is not None else None,
            evidence=(
                f"{witness.name}: route-legal active skill explicitly grants Major/Minor Resolve"
            ),
        )


__all__ = [
    "GRANTS_RESOLVE",
    "ExtremeActualHealSetupActionWitness",
    "ExtremeActualHealSetupActionLegalityService",
]
