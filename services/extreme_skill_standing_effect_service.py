from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minmax.gear_stat_inputs import GearStatInputResolver
from services.named_buff_resolution_service import (
    NamedBuffContribution,
    NamedBuffResolutionService,
)


class ExtremeSkillEffectScope(str, Enum):
    ACTIVE_BAR_SLOTTED = "active_bar_slotted"
    EITHER_BAR_SLOTTED = "either_bar_slotted"
    ACTIVATED_RUNTIME = "activated_runtime"


@dataclass(frozen=True)
class ExtremeSkillStandingEffect:
    skill_name: str
    objective_key: str
    projected_delta: float
    source: str
    scope: ExtremeSkillEffectScope
    stacking_key: str


class ExtremeSkillStandingEffectService:
    """Reviewed skill effects usable by Extreme bar selection."""

    MAJOR_CRIT_RATING = 2629.0
    MINOR_RESOLVE_ARMOR = 2974.0
    MAJOR_BRUTALITY_SORCERY_PERCENT = 0.20

    _MAJOR_CRIT_EITHER_BAR = frozenset(
        {"grim focus", "relentless focus", "merciless resolve", "bound armaments"}
    )
    _MINOR_RESOLVE_EITHER_BAR = frozenset({"bound aegis"})
    _MAJOR_POWER_EITHER_BAR = frozenset(
        {"tome-bearer's inspiration", "inspired scholarship", "recuperative treatise"}
    )

    @classmethod
    def effects_for_skill(
        cls,
        skill_name: str,
        *,
        reference_value: float | None = None,
    ) -> tuple[ExtremeSkillStandingEffect, ...]:
        name = " ".join(str(skill_name or "").strip().casefold().split())
        if not name:
            return ()
        label = str(skill_name or "").strip()

        if name in cls._MAJOR_CRIT_EITHER_BAR:
            ratio = GearStatInputResolver.critical_rating_to_ratio(cls.MAJOR_CRIT_RATING)
            source = f"{label}: reviewed either-bar Major Prophecy/Savagery"
            return (
                ExtremeSkillStandingEffect(label, "spell_critical", ratio, source, ExtremeSkillEffectScope.EITHER_BAR_SLOTTED, "major_prophecy"),
                ExtremeSkillStandingEffect(label, "weapon_critical", ratio, source, ExtremeSkillEffectScope.EITHER_BAR_SLOTTED, "major_savagery"),
            )

        if name in cls._MINOR_RESOLVE_EITHER_BAR:
            source = f"{label}: reviewed either-bar Minor Resolve armor"
            return (
                ExtremeSkillStandingEffect(label, "physical_resistance", cls.MINOR_RESOLVE_ARMOR, source, ExtremeSkillEffectScope.EITHER_BAR_SLOTTED, "minor_resolve"),
                ExtremeSkillStandingEffect(label, "spell_resistance", cls.MINOR_RESOLVE_ARMOR, source, ExtremeSkillEffectScope.EITHER_BAR_SLOTTED, "minor_resolve"),
            )

        if name in cls._MAJOR_POWER_EITHER_BAR:
            if reference_value is None:
                return ()
            delta = float(reference_value) * cls.MAJOR_BRUTALITY_SORCERY_PERCENT
            source = (
                f"{label}: reviewed either-bar Major Brutality/Sorcery "
                f"({cls.MAJOR_BRUTALITY_SORCERY_PERCENT:.0%} of reference power)"
            )
            return (
                ExtremeSkillStandingEffect(label, "spell_damage", delta, source, ExtremeSkillEffectScope.EITHER_BAR_SLOTTED, "major_sorcery"),
                ExtremeSkillStandingEffect(label, "weapon_damage", delta, source, ExtremeSkillEffectScope.EITHER_BAR_SLOTTED, "major_brutality"),
            )

        return ()

    @staticmethod
    def stack_effects(effects: tuple[ExtremeSkillStandingEffect, ...]) -> tuple[ExtremeSkillStandingEffect, ...]:
        return NamedBuffResolutionService.resolve(effects)

    @classmethod
    def score(cls, skill_name: str, objective_key: str, *, reference_value: float | None = None) -> float:
        objective = str(objective_key or "").strip()
        return sum(
            float(effect.projected_delta)
            for effect in cls.effects_for_skill(skill_name, reference_value=reference_value)
            if effect.objective_key == objective and effect.scope is not ExtremeSkillEffectScope.ACTIVATED_RUNTIME
        )

    @classmethod
    def marginal_score(
        cls,
        skill_name: str,
        objective_key: str,
        *,
        reference_value: float | None = None,
        external_effects: tuple[NamedBuffContribution, ...] = (),
    ) -> float:
        objective = str(objective_key or "").strip()
        baseline, _ = NamedBuffResolutionService.score(
            tuple(effect for effect in external_effects if effect.objective_key == objective),
            objective_key=objective,
        )
        skill_effects = tuple(
            effect
            for effect in cls.effects_for_skill(skill_name, reference_value=reference_value)
            if effect.objective_key == objective and effect.scope is not ExtremeSkillEffectScope.ACTIVATED_RUNTIME
        )
        combined, _ = NamedBuffResolutionService.score(
            tuple((*external_effects, *skill_effects)),
            objective_key=objective,
        )
        return combined - baseline

    @classmethod
    def sources(cls, skill_name: str, objective_key: str, *, reference_value: float | None = None) -> tuple[str, ...]:
        objective = str(objective_key or "").strip()
        return tuple(
            effect.source
            for effect in cls.effects_for_skill(skill_name, reference_value=reference_value)
            if effect.objective_key == objective and effect.scope is not ExtremeSkillEffectScope.ACTIVATED_RUNTIME
        )

    @classmethod
    def _standing_bar_effects(
        cls,
        front_skill_names: tuple[str, ...],
        back_skill_names: tuple[str, ...],
        objective_key: str,
        *,
        active_bar: str,
        reference_value: float | None,
    ) -> tuple[ExtremeSkillStandingEffect, ...]:
        active = str(active_bar or "").strip().casefold()
        if active not in {"front", "back"}:
            raise ValueError("active_bar must be 'front' or 'back'")
        active_names = front_skill_names if active == "front" else back_skill_names
        candidates: list[ExtremeSkillStandingEffect] = []
        for skill_name in tuple(dict.fromkeys((*front_skill_names, *back_skill_names))):
            for effect in cls.effects_for_skill(skill_name, reference_value=reference_value):
                if effect.objective_key == objective_key and effect.scope is ExtremeSkillEffectScope.EITHER_BAR_SLOTTED:
                    candidates.append(effect)
        for skill_name in active_names:
            for effect in cls.effects_for_skill(skill_name, reference_value=reference_value):
                if effect.objective_key == objective_key and effect.scope is ExtremeSkillEffectScope.ACTIVE_BAR_SLOTTED:
                    candidates.append(effect)
        return tuple(candidates)

    @classmethod
    def score_build_bars(
        cls,
        front_skill_names: tuple[str, ...],
        back_skill_names: tuple[str, ...],
        objective_key: str,
        *,
        active_bar: str,
        reference_value: float | None = None,
        external_effects: tuple[NamedBuffContribution, ...] = (),
    ) -> tuple[float, tuple[str, ...]]:
        candidates = list(
            cls._standing_bar_effects(
                front_skill_names,
                back_skill_names,
                objective_key,
                active_bar=active_bar,
                reference_value=reference_value,
            )
        )
        candidates.extend(effect for effect in external_effects if effect.objective_key == objective_key)
        selected = NamedBuffResolutionService.resolve(tuple(candidates))
        return (
            sum(float(effect.projected_delta) for effect in selected),
            tuple(effect.source for effect in selected),
        )

    @classmethod
    def marginal_score_build_bars_explained(
        cls,
        front_skill_names: tuple[str, ...],
        back_skill_names: tuple[str, ...],
        objective_key: str,
        *,
        active_bar: str,
        reference_value: float | None = None,
        external_effects: tuple[NamedBuffContribution, ...] = (),
    ) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
        external = tuple(effect for effect in external_effects if effect.objective_key == objective_key)
        baseline, _ = NamedBuffResolutionService.score(external, objective_key=objective_key)
        skill_effects = cls._standing_bar_effects(
            front_skill_names,
            back_skill_names,
            objective_key,
            active_bar=active_bar,
            reference_value=reference_value,
        )
        resolution = NamedBuffResolutionService.explain(tuple((*external, *skill_effects)), objective_key=objective_key)
        total = sum(float(effect.projected_delta) for effect in resolution.selected)
        notes = tuple(
            f"{item.suppressed_source} suppressed by {item.retained_source}: {item.reason}"
            for item in resolution.suppressed
        )
        return total - baseline, tuple(str(effect.source) for effect in resolution.selected), notes

    @classmethod
    def marginal_score_build_bars(
        cls,
        front_skill_names: tuple[str, ...],
        back_skill_names: tuple[str, ...],
        objective_key: str,
        *,
        active_bar: str,
        reference_value: float | None = None,
        external_effects: tuple[NamedBuffContribution, ...] = (),
    ) -> tuple[float, tuple[str, ...]]:
        delta, sources, _ = cls.marginal_score_build_bars_explained(
            front_skill_names,
            back_skill_names,
            objective_key,
            active_bar=active_bar,
            reference_value=reference_value,
            external_effects=external_effects,
        )
        return delta, sources
