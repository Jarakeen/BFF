from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minmax.gear_stat_inputs import GearStatInputResolver
from services.named_buff_resolution_service import NamedBuffResolutionService


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
    """Reviewed skill effects usable by Extreme bar selection.

    Effects carry an explicit activation scope. Some ESO bonuses require the
    skill on the active bar, some apply when the skill is slotted on either bar,
    and activated/runtime effects are intentionally excluded from resting-sheet
    scoring until combat state supplies their uptime.

    Named-buff stacking is delegated to the source-neutral resolver shared with
    future potion, set, passive, and group-provider effects. Source type does not
    create a second copy of the same named Major/Minor buff.
    """

    MAJOR_CRIT_RATING = 2629.0
    MINOR_RESOLVE_ARMOR = 2974.0
    MAJOR_BRUTALITY_SORCERY_PERCENT = 0.20

    _MAJOR_CRIT_EITHER_BAR = frozenset(
        {
            "grim focus",
            "relentless focus",
            "merciless resolve",
            "bound armaments",
        }
    )

    _MINOR_RESOLVE_EITHER_BAR = frozenset({"bound aegis"})

    _MAJOR_POWER_EITHER_BAR = frozenset(
        {
            "tome-bearer's inspiration",
            "inspired scholarship",
            "recuperative treatise",
        }
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
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="spell_critical",
                    projected_delta=ratio,
                    source=source,
                    scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
                    stacking_key="major_prophecy",
                ),
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="weapon_critical",
                    projected_delta=ratio,
                    source=source,
                    scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
                    stacking_key="major_savagery",
                ),
            )

        if name in cls._MINOR_RESOLVE_EITHER_BAR:
            source = f"{label}: reviewed either-bar Minor Resolve armor"
            return (
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="physical_resistance",
                    projected_delta=cls.MINOR_RESOLVE_ARMOR,
                    source=source,
                    scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
                    stacking_key="minor_resolve",
                ),
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="spell_resistance",
                    projected_delta=cls.MINOR_RESOLVE_ARMOR,
                    source=source,
                    scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
                    stacking_key="minor_resolve",
                ),
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
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="spell_damage",
                    projected_delta=delta,
                    source=source,
                    scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
                    stacking_key="major_sorcery",
                ),
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="weapon_damage",
                    projected_delta=delta,
                    source=source,
                    scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
                    stacking_key="major_brutality",
                ),
            )

        return ()

    @staticmethod
    def stack_effects(
        effects: tuple[ExtremeSkillStandingEffect, ...],
    ) -> tuple[ExtremeSkillStandingEffect, ...]:
        """Apply the shared ESO named-buff stacking contract."""
        return NamedBuffResolutionService.resolve(effects)

    @classmethod
    def score(
        cls,
        skill_name: str,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> float:
        objective = str(objective_key or "").strip()
        return sum(
            float(effect.projected_delta)
            for effect in cls.effects_for_skill(skill_name, reference_value=reference_value)
            if effect.objective_key == objective
            and effect.scope is not ExtremeSkillEffectScope.ACTIVATED_RUNTIME
        )

    @classmethod
    def sources(
        cls,
        skill_name: str,
        objective_key: str,
        *,
        reference_value: float | None = None,
    ) -> tuple[str, ...]:
        objective = str(objective_key or "").strip()
        return tuple(
            effect.source
            for effect in cls.effects_for_skill(skill_name, reference_value=reference_value)
            if effect.objective_key == objective
            and effect.scope is not ExtremeSkillEffectScope.ACTIVATED_RUNTIME
        )

    @classmethod
    def score_build_bars(
        cls,
        front_skill_names: tuple[str, ...],
        back_skill_names: tuple[str, ...],
        objective_key: str,
        *,
        active_bar: str,
        reference_value: float | None = None,
    ) -> tuple[float, tuple[str, ...]]:
        """Score reviewed standing skill effects with bar scope and buff stacking."""
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

        selected = cls.stack_effects(tuple(candidates))
        return (
            sum(float(effect.projected_delta) for effect in selected),
            tuple(effect.source for effect in selected),
        )
