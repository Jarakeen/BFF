from __future__ import annotations

from dataclasses import dataclass

from minmax.gear_stat_inputs import GearStatInputResolver


@dataclass(frozen=True)
class ExtremeSkillStandingEffect:
    skill_name: str
    objective_key: str
    projected_delta: float
    source: str


class ExtremeSkillStandingEffectService:
    """Reviewed active-skill standing effects usable by Extreme bar selection.

    This is intentionally not a tooltip parser. Only mechanics with a reviewed
    numeric interpretation are admitted here. Triggered/cast-dependent effects
    stay out until their combat-state boundary is modeled explicitly.

    Flat/rating effects can project without a reference stat. Percentage effects
    require the caller's objective-specific reference value; without it they
    remain unscored rather than being mistaken for a tiny flat delta.
    """

    MAJOR_CRIT_RATING = 2629.0
    MINOR_RESOLVE_ARMOR = 2974.0
    MAJOR_BRUTALITY_SORCERY_PERCENT = 0.20

    _MAJOR_CRIT_WHILE_SLOTTED = frozenset(
        {
            "relentless focus",
            "merciless resolve",
            "bound armaments",
        }
    )

    _MINOR_RESOLVE_WHILE_SLOTTED = frozenset(
        {
            "bound aegis",
        }
    )

    _MAJOR_POWER_WHILE_SLOTTED = frozenset(
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

        if name in cls._MAJOR_CRIT_WHILE_SLOTTED:
            ratio = GearStatInputResolver.critical_rating_to_ratio(cls.MAJOR_CRIT_RATING)
            source = f"{label}: reviewed while-slotted Major critical rating"
            return (
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="spell_critical",
                    projected_delta=ratio,
                    source=source,
                ),
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="weapon_critical",
                    projected_delta=ratio,
                    source=source,
                ),
            )

        if name in cls._MINOR_RESOLVE_WHILE_SLOTTED:
            source = f"{label}: reviewed while-slotted Minor Resolve armor"
            return (
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="physical_resistance",
                    projected_delta=cls.MINOR_RESOLVE_ARMOR,
                    source=source,
                ),
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="spell_resistance",
                    projected_delta=cls.MINOR_RESOLVE_ARMOR,
                    source=source,
                ),
            )

        if name in cls._MAJOR_POWER_WHILE_SLOTTED:
            if reference_value is None:
                return ()
            delta = float(reference_value) * cls.MAJOR_BRUTALITY_SORCERY_PERCENT
            source = (
                f"{label}: reviewed while-slotted Major Brutality/Sorcery "
                f"({cls.MAJOR_BRUTALITY_SORCERY_PERCENT:.0%} of reference power)"
            )
            return (
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="spell_damage",
                    projected_delta=delta,
                    source=source,
                ),
                ExtremeSkillStandingEffect(
                    skill_name=label,
                    objective_key="weapon_damage",
                    projected_delta=delta,
                    source=source,
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
            for effect in cls.effects_for_skill(
                skill_name,
                reference_value=reference_value,
            )
            if effect.objective_key == objective
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
            for effect in cls.effects_for_skill(
                skill_name,
                reference_value=reference_value,
            )
            if effect.objective_key == objective
        )
