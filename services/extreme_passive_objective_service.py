from __future__ import annotations

"""Route-aware passive scoring for Extreme Build objectives."""

from dataclasses import dataclass

from services.extreme_passive_projection_service import (
    ExtremePassiveContribution,
    ExtremePassiveProjection,
    ExtremePassiveProjectionService,
    ExtremePassiveProjectionStatus,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _key(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


@dataclass(frozen=True)
class ExtremePassiveLegalityContext:
    equipped_class_lines: tuple[str, ...]
    equipped_weapon_lines: tuple[str, ...] = ()
    selected_racial_line: str | None = None
    available_shared_lines: tuple[str, ...] = ()
    vampire: bool = False
    werewolf: bool = False

    def __post_init__(self) -> None:
        if self.vampire and self.werewolf:
            raise ValueError("A player route cannot be both Vampire and Werewolf")


@dataclass(frozen=True)
class ExtremePassiveObjectiveResult:
    objective_key: str
    projected_delta: float
    contributions: tuple[ExtremePassiveContribution, ...]
    unresolved_passives: tuple[str, ...]
    context_required_passives: tuple[str, ...]

    @property
    def fully_resolved(self) -> bool:
        return not self.unresolved_passives and not self.context_required_passives


class ExtremePassiveObjectiveService:
    """Apply only legal, reviewed passive projections for one Extreme route."""

    @staticmethod
    def _legal(
        passive: ExtremePlayerSkillRecord,
        context: ExtremePassiveLegalityContext,
    ) -> bool:
        line = passive.line_key
        if passive.domain is ExtremeSkillDomain.CLASS:
            return line in {_key(value) for value in context.equipped_class_lines}
        if passive.domain is ExtremeSkillDomain.WEAPON:
            return line in {_key(value) for value in context.equipped_weapon_lines}
        if passive.domain is ExtremeSkillDomain.RACIAL:
            return bool(context.selected_racial_line) and line == _key(context.selected_racial_line)
        if passive.domain is ExtremeSkillDomain.WORLD:
            if line == "vampire":
                return context.vampire
            if line == "werewolf":
                return context.werewolf
        if passive.domain in {
            ExtremeSkillDomain.GUILD,
            ExtremeSkillDomain.ALLIANCE_WAR,
            ExtremeSkillDomain.WORLD,
            ExtremeSkillDomain.ARMOR,
            ExtremeSkillDomain.CRAFT,
            ExtremeSkillDomain.UTILITY,
            ExtremeSkillDomain.OTHER,
        }:
            available = {_key(value) for value in context.available_shared_lines}
            # Empty means the Extreme/max-rank route may own ordinary shared
            # lines; explicit availability restricts saved-character contexts.
            return not available or line in available
        return False

    @classmethod
    def score(
        cls,
        passives: tuple[ExtremePlayerSkillRecord, ...],
        objective_key: str,
        context: ExtremePassiveLegalityContext,
        *,
        reference_value: float | None = None,
    ) -> ExtremePassiveObjectiveResult:
        objective = _key(objective_key)
        if objective not in ExtremePassiveProjectionService.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme passive objective: {objective_key!r}")

        contributions: list[ExtremePassiveContribution] = []
        unresolved: list[str] = []
        contextual: list[str] = []

        for passive in passives:
            if not passive.is_passive or not cls._legal(passive, context):
                continue
            projection: ExtremePassiveProjection = ExtremePassiveProjectionService.project(passive)
            if projection.status is ExtremePassiveProjectionStatus.KNOWN_NONCOMBAT:
                continue
            if projection.status is ExtremePassiveProjectionStatus.CONTEXT_REQUIRED:
                contextual.append(f"{passive.skill_line}: {passive.name}")
                continue
            if projection.status is ExtremePassiveProjectionStatus.UNRESOLVED:
                unresolved.append(f"{passive.skill_line}: {passive.name}")
                continue

            for contribution in projection.contributions:
                if contribution.objective_key != objective:
                    continue
                projected = contribution.projected_delta(reference_value)
                if projected is None:
                    contextual.append(
                        f"{passive.skill_line}: {passive.name} requires reference value for {objective}"
                    )
                    continue
                contributions.append(contribution)

        total = sum(
            float(contribution.projected_delta(reference_value) or 0.0)
            for contribution in contributions
        )
        return ExtremePassiveObjectiveResult(
            objective_key=objective,
            projected_delta=total,
            contributions=tuple(contributions),
            unresolved_passives=tuple(sorted(set(unresolved), key=str.casefold)),
            context_required_passives=tuple(sorted(set(contextual), key=str.casefold)),
        )
