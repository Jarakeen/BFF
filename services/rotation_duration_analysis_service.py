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
from minmax.skill_coefficient_repository import SkillCoefficientRepository
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_duration_repository import SkillDurationRepository
from services.rotation_reviewed_skill_component_repository import (
    RotationReviewedSkillComponentRepository,
)
from services.rotation_scribed_skill_damage_semantics_service import (
    RotationScribedSkillDamageSemanticsService,
)


@dataclass(frozen=True)
class RotationDurationProjection:
    analysis: RotationRecastAnalysis
    rules: tuple[RotationRecastRule, ...]
    unresolved: tuple[str, ...]
    effective_duration_overrides: tuple[RotationEffectiveDurationOverride, ...] = ()


class RotationDurationAnalysisService:
    """Resolve build-effective recast semantics and audit finite durations.

    Canonical skill duration remains the fallback evidence. When an upstream
    authoritative build/effect resolver supplies an already-resolved effective
    duration, that value is used for recast and uptime math instead. Reviewed
    persistent toggles emit explicit persistent recast rules with no fabricated
    finite duration. Those rules participate in scheduling but are excluded from the
    finite-duration analyzer because exact toggle lifetime belongs to runtime state.

    A reviewed skill whose coefficient-bearing components are all proven immediate
    non-periodic damage requires no finite-duration recast rule. This distinction is
    intentionally evidence-driven: an absent/zero canonical duration by itself does
    not prove that a skill is instantaneous, so unknown, mixed, healing, utility, or
    periodic component identity continues to fail closed.
    """

    def __init__(
        self,
        database_path: Path = DEFAULT_DATABASE,
        *,
        duration_repository: SkillDurationRepository | None = None,
        analyzer: RotationRecastAnalyzer | None = None,
        scribed_skill_semantics: RotationScribedSkillDamageSemanticsService | None = None,
        coefficient_repository: SkillCoefficientRepository | None = None,
        reviewed_component_repository: RotationReviewedSkillComponentRepository | None = None,
    ) -> None:
        database = Path(database_path)
        self.duration_repository = duration_repository or SkillDurationRepository(database)
        self.analyzer = analyzer or RotationRecastAnalyzer()
        self.scribed_skill_semantics = (
            scribed_skill_semantics or RotationScribedSkillDamageSemanticsService()
        )
        self.coefficient_repository = (
            coefficient_repository or SkillCoefficientRepository(database)
        )
        self.reviewed_component_repository = (
            reviewed_component_repository
            or RotationReviewedSkillComponentRepository(database)
        )

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

            scribed = self.scribed_skill_semantics.resolve(action.name)
            if scribed is not None and scribed.persistent_toggle:
                rules.append(
                    RotationRecastRule(
                        skill_name=scribed.result_name,
                        duration_seconds=None,
                        bar=action.bar,
                        persistent=True,
                    )
                )
                continue

            resolution = self.duration_repository.resolve_name(action.name)
            if resolution.duration_seconds is None:
                if self._is_reviewed_immediate_damage_skill(action.name):
                    continue
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

        finite_rules = tuple(rule for rule in rules if not rule.persistent)
        analysis = self.analyzer.analyze(plan, finite_rules)
        unresolved.extend(analysis.unresolved)
        return RotationDurationProjection(
            analysis=analysis,
            rules=tuple(rules),
            unresolved=self._dedupe(unresolved),
            effective_duration_overrides=tuple(applied_overrides),
        )

    def _is_reviewed_immediate_damage_skill(self, skill_name: str) -> bool:
        """Return True only for reviewed all-direct, non-periodic damage identity."""

        resolution = self.coefficient_repository.resolve_entity_id(skill_name)
        if resolution.rank is None:
            return False

        components = self.reviewed_component_repository.get_for_skill_rank(
            resolution.rank.skill_rank_id
        )
        if not components:
            return False

        coefficient_numbers = {
            int(coefficient.coefficient_number)
            for coefficient in resolution.rank.coefficients
        }
        if not coefficient_numbers:
            return False

        by_number = {
            int(component.coefficient_number): component
            for component in components
        }
        reviewed = [by_number.get(number) for number in sorted(coefficient_numbers)]
        if any(component is None for component in reviewed):
            return False

        return all(
            component.effect_kind is SkillEffectKind.DAMAGE
            and component.is_dot is False
            for component in reviewed
            if component is not None
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
