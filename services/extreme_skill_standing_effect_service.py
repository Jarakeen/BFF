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

    This is intentionally not a tooltip parser. Only mechanics already modeled
    elsewhere in BFF are admitted here. Triggered/cast-dependent effects stay out
    until their combat-state boundary is modeled explicitly.
    """

    MAJOR_CRIT_RATING = 2629.0

    _MAJOR_CRIT_WHILE_SLOTTED = frozenset(
        {
            "relentless focus",
            "merciless resolve",
        }
    )

    @classmethod
    def effects_for_skill(cls, skill_name: str) -> tuple[ExtremeSkillStandingEffect, ...]:
        name = " ".join(str(skill_name or "").strip().casefold().split())
        if not name:
            return ()

        if name in cls._MAJOR_CRIT_WHILE_SLOTTED:
            ratio = GearStatInputResolver.critical_rating_to_ratio(cls.MAJOR_CRIT_RATING)
            label = str(skill_name or "").strip()
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

        return ()

    @classmethod
    def score(cls, skill_name: str, objective_key: str) -> float:
        objective = str(objective_key or "").strip()
        return sum(
            float(effect.projected_delta)
            for effect in cls.effects_for_skill(skill_name)
            if effect.objective_key == objective
        )

    @classmethod
    def sources(cls, skill_name: str, objective_key: str) -> tuple[str, ...]:
        objective = str(objective_key or "").strip()
        return tuple(
            effect.source
            for effect in cls.effects_for_skill(skill_name)
            if effect.objective_key == objective
        )
