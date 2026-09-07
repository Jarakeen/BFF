from __future__ import annotations

from dataclasses import dataclass

from services.extreme_skill_standing_effect_service import ExtremeSkillStandingEffectService
from services.named_buff_resolution_service import NamedBuffContribution


@dataclass(frozen=True)
class ExtremeBuffContextExplanation:
    objective_key: str
    marginal_delta: float
    retained_sources: tuple[str, ...]
    suppression_notes: tuple[str, ...]

    @property
    def has_redundancy(self) -> bool:
        return bool(self.suppression_notes)


class ExtremeBuffContextExplanationService:
    """Explain how external named buffs change the value of one two-bar build.

    This is deliberately presentation-ready but source-neutral. Callers such as
    Comp Maker can pass potion, set, passive, or group-provider contributions and
    show why a reviewed skill stopped adding value without reimplementing ESO's
    named-buff stacking rules.
    """

    @staticmethod
    def explain_build(
        front_skill_names: tuple[str, ...],
        back_skill_names: tuple[str, ...],
        objective_key: str,
        *,
        active_bar: str,
        reference_value: float | None = None,
        external_effects: tuple[NamedBuffContribution, ...] = (),
    ) -> ExtremeBuffContextExplanation:
        delta, sources, notes = ExtremeSkillStandingEffectService.marginal_score_build_bars_explained(
            front_skill_names,
            back_skill_names,
            objective_key,
            active_bar=active_bar,
            reference_value=reference_value,
            external_effects=external_effects,
        )
        return ExtremeBuffContextExplanation(
            objective_key=objective_key,
            marginal_delta=delta,
            retained_sources=sources,
            suppression_notes=notes,
        )
