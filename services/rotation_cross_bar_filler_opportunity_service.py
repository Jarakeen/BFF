from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_duration_analysis_service import RotationDurationAnalysisService


@dataclass(frozen=True)
class RotationCrossBarFillerOpportunity:
    wait_time_seconds: float
    wait_bar: str
    target_bar: str
    filler_skill_name: str
    filler_priority: int | None = None


class RotationCrossBarFillerOpportunityService:
    """Identify fail-closed opportunities to replace WAITs via a bar swap.

    This service is diagnostic only. It does not mutate the rotation plan or invent
    swap timing. A candidate filler is eligible only when canonical duration analysis
    proves that the exact skill has no finite/persistent recast rule and no unresolved
    duration evidence. This deliberately distinguishes a reviewed immediate action
    from a skill whose duration is merely unknown.

    When explicit ability priorities are supplied, the highest-priority eligible
    opposite-bar filler is reported first. Without priorities, deterministic plan
    appearance order is used and no gameplay preference is inferred.
    """

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        duration_analysis: RotationDurationAnalysisService | None = None,
    ) -> None:
        self.duration_analysis = duration_analysis or RotationDurationAnalysisService(
            database_path=database_path,
        )

    def find(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList | None = None,
    ) -> tuple[RotationCrossBarFillerOpportunity, ...]:
        skills_by_bar = self._skills_by_bar(plan)
        priority_rank = self._priority_rank(priorities)
        opportunities: list[RotationCrossBarFillerOpportunity] = []

        for action in plan.actions:
            if action.kind is not RotationActionKind.WAIT:
                continue
            wait_bar = str(action.bar or "").strip().casefold()
            if wait_bar not in {"front", "back"}:
                continue
            target_bar = "back" if wait_bar == "front" else "front"
            candidates = [
                name
                for name in skills_by_bar[target_bar]
                if self._is_reviewed_immediate(name, target_bar)
            ]
            if not candidates:
                continue

            if priorities is not None:
                candidates.sort(
                    key=lambda name: priority_rank.get(
                        (target_bar, name.casefold()),
                        (10**9, 10**9),
                    )
                )
            filler = candidates[0]
            rank = priority_rank.get((target_bar, filler.casefold()))
            opportunities.append(
                RotationCrossBarFillerOpportunity(
                    wait_time_seconds=float(action.time_seconds),
                    wait_bar=wait_bar,
                    target_bar=target_bar,
                    filler_skill_name=filler,
                    filler_priority=(rank[0] if rank is not None else None),
                )
            )

        return tuple(opportunities)

    def _is_reviewed_immediate(self, skill_name: str, bar: str) -> bool:
        probe = RotationPlan(
            character_name="cross-bar-filler-probe",
            build_name="cross-bar-filler-probe",
            duration_seconds=1.0,
            actions=(
                RotationAction(
                    time_seconds=0.0,
                    sequence=1,
                    kind=RotationActionKind.SKILL,
                    name=skill_name,
                    bar=bar,
                ),
            ),
        )
        projection = self.duration_analysis.analyze(probe)
        return not projection.rules and not projection.unresolved

    @staticmethod
    def _skills_by_bar(plan: RotationPlan) -> dict[str, tuple[str, ...]]:
        result: dict[str, list[str]] = {"front": [], "back": []}
        seen: dict[str, set[str]] = {"front": set(), "back": set()}
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            bar = str(action.bar or "").strip().casefold()
            if bar not in result:
                continue
            key = action.name.casefold()
            if key in seen[bar]:
                continue
            seen[bar].add(key)
            result[bar].append(action.name)
        return {bar: tuple(values) for bar, values in result.items()}

    @staticmethod
    def _priority_rank(
        priorities: AbilityPriorityList | None,
    ) -> dict[tuple[str, str], tuple[int, int]]:
        if priorities is None:
            return {}
        return {
            (item.entry.bar, item.entry.skill_name.casefold()): (
                item.effective_priority,
                item.entry.slot,
            )
            for item in priorities.resolve()
        }


__all__ = [
    "RotationCrossBarFillerOpportunity",
    "RotationCrossBarFillerOpportunityService",
]
