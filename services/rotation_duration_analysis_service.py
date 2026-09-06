from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.rotation_recast import (
    RotationRecastAnalysis,
    RotationRecastAnalyzer,
    RotationRecastRule,
)
from minmax.skill_duration_repository import SkillDurationRepository


@dataclass(frozen=True)
class RotationDurationProjection:
    analysis: RotationRecastAnalysis
    rules: tuple[RotationRecastRule, ...]
    unresolved: tuple[str, ...]


class RotationDurationAnalysisService:
    """Resolve canonical skill durations and audit a generated rotation's recasts."""

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        duration_repository: SkillDurationRepository | None = None,
        analyzer: RotationRecastAnalyzer | None = None,
    ) -> None:
        self.duration_repository = duration_repository or SkillDurationRepository(database_path)
        self.analyzer = analyzer or RotationRecastAnalyzer()

    def analyze(self, plan: RotationPlan) -> RotationDurationProjection:
        rules: list[RotationRecastRule] = []
        unresolved: list[str] = []
        seen: set[tuple[str, str | None]] = set()

        for action in plan.actions:
            if action.kind not in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
                continue
            if not action.name:
                continue
            key = (action.name.casefold(), action.bar)
            if key in seen:
                continue
            seen.add(key)

            resolution = self.duration_repository.resolve_name(action.name)
            if resolution.duration_seconds is None:
                unresolved.extend(
                    f"{action.name}: {message}" for message in resolution.unresolved
                )
                continue

            rules.append(
                RotationRecastRule(
                    skill_name=resolution.skill_name or action.name,
                    duration_seconds=resolution.duration_seconds,
                    bar=action.bar,
                )
            )

        analysis = self.analyzer.analyze(plan, tuple(rules))
        unresolved.extend(analysis.unresolved)
        return RotationDurationProjection(
            analysis=analysis,
            rules=tuple(rules),
            unresolved=self._dedupe(unresolved),
        )

    @staticmethod
    def _dedupe(values: list[str]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)
