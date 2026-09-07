from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.rotation_effective_duration import (
    RotationEffectiveDurationOverride,
    index_effective_duration_overrides,
    select_effective_duration_override,
)
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
    effective_duration_overrides: tuple[RotationEffectiveDurationOverride, ...] = ()


class RotationDurationAnalysisService:
    """Resolve build-effective skill durations and audit rotation recasts.

    Canonical skill duration remains the fallback evidence. When an upstream
    authoritative build/effect resolver supplies an already-resolved effective
    duration, that value is used for recast and uptime math instead. This service
    does not calculate gear/passive/armor duration mechanics itself.
    """

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        duration_repository: SkillDurationRepository | None = None,
        analyzer: RotationRecastAnalyzer | None = None,
    ) -> None:
        self.duration_repository = duration_repository or SkillDurationRepository(database_path)
        self.analyzer = analyzer or RotationRecastAnalyzer()

    def analyze(
        self,
        plan: RotationPlan,
        *,
        effective_duration_overrides: tuple[RotationEffectiveDurationOverride, ...] = (),
    ) -> RotationDurationProjection:
        indexed_overrides = index_effective_duration_overrides(
            tuple(effective_duration_overrides)
        )
        rules: list[RotationRecastRule] = []
        unresolved: list[str] = []
        applied_overrides: list[RotationEffectiveDurationOverride] = []
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

            override = select_effective_duration_override(
                indexed_overrides,
                skill_name=resolution.skill_name or action.name,
                bar=action.bar,
            )
            duration_seconds = (
                override.duration_seconds
                if override is not None
                else resolution.duration_seconds
            )
            if override is not None:
                applied_overrides.append(override)

            rules.append(
                RotationRecastRule(
                    skill_name=resolution.skill_name or action.name,
                    duration_seconds=duration_seconds,
                    bar=action.bar,
                )
            )

        analysis = self.analyzer.analyze(plan, tuple(rules))
        unresolved.extend(analysis.unresolved)
        return RotationDurationProjection(
            analysis=analysis,
            rules=tuple(rules),
            unresolved=self._dedupe(unresolved),
            effective_duration_overrides=tuple(applied_overrides),
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
