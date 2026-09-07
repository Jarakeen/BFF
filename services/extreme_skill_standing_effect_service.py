from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minmax.gear_stat_inputs import GearStatInputResolver


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

    Named buffs also carry a stacking key so two sources of the same Major/Minor
    buff do not get added together merely because both skills are slotted.
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
                    stacking_key="major_prophecy_savagery",
                ),
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="weapon_critical",
                    projected_delta=ratio,
                    source=source,
                    scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
                    stacking_key="major_prophecy_savagery",
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
                    stacking_key="major_brutality_sorcery",
                ),
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="weapon_damage",
                    projected_delta=delta,
                    source=source,
                    scope=ExtremeSkillEffectScope.EITHER_BAR_SLOTTED,
                    stacking_key="major_brutality_sorcery",
                ),
            )

        return ()

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
        """Score reviewed standing skill effects with bar scope and buff stacking.

        Either-bar effects are considered from the union of both bars and count
        once per named stacking key. Active-bar effects are considered only from
        the selected active bar. Activated/runtime effects are never projected
        here.
        """
        active = str(active_bar or "").strip().casefold()
        if active not in {"front", "back"}:
            raise ValueError("active_bar must be 'front' or 'back'")

        active_names = front_skill_names if active == "front" else back_skill_names
        candidates: list[ExtremeSkillStandingEffect] = []

        for skill_name in tuple(dict.fromkeys((*front_skill_names, *back_skill_names))):
            for effect in cls.effects_for_skill(skill_name, reference_value=reference_value):
                if effect.objective_key != objective_key:
                    continue
                if effect.scope is ExtremeSkillEffectScope.EITHER_BAR_SLOTTED:
                    candidates.append(effect)

        for skill_name in active_names:
            for effect in cls.effects_for_skill(skill_name, reference_value=reference_value):
                if effect.objective_key != objective_key:
                    continue
                if effect.scope is ExtremeSkillEffectScope.ACTIVE_BAR_SLOTTED:
                    candidates.append(effect)

        by_key: dict[str, ExtremeSkillStandingEffect] = {}
        for effect in candidates:
            existing = by_key.get(effect.stacking_key)
            if existing is None or effect.projected_delta > existing.projected_delta:
                by_key[effect.stacking_key] = effect

        selected = tuple(by_key[key] for key in sorted(by_key))
        return (
            sum(float(effect.projected_delta) for effect in selected),
            tuple(effect.source for effect in selected),
        )
