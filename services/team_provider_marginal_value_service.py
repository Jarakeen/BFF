from __future__ import annotations

from dataclasses import dataclass

from services.named_buff_resolution_service import (
    NamedBuffContribution,
    NamedBuffResolutionService,
    NamedBuffSuppression,
)


@dataclass(frozen=True)
class TeamProviderMarginalValue:
    """Source-neutral marginal provider value against an existing team context.

    This deliberately does not collapse unlike ESO objectives into one synthetic
    number. Damage, resistance, recovery, critical chance, and other objectives
    use different units. Consumers may use ``new_named_effect_count`` as a safe
    tie-break signal when their primary canonical objective is already tied, while
    retaining per-objective deltas for explanation and later raid-scale scoring.
    """

    marginal_effects: tuple[NamedBuffContribution, ...]
    suppressed: tuple[NamedBuffSuppression, ...]
    objective_deltas: tuple[tuple[str, float], ...]

    @property
    def new_named_effect_count(self) -> int:
        # One ESO named buff is one provider signal even when our model records
        # that buff against multiple objectives (for example Minor Resolve affects
        # both physical and spell resistance). Do not reward schema width.
        return len(self.stacking_keys)

    @property
    def stacking_keys(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    NamedBuffResolutionService.canonical_key(effect.stacking_key)
                    for effect in self.marginal_effects
                }
            )
        )

    def delta_for(self, objective_key: str) -> float:
        objective = str(objective_key or "").strip()
        return next(
            (value for key, value in self.objective_deltas if key == objective),
            0.0,
        )


class TeamProviderMarginalValueService:
    """Measure only the named effects a candidate adds beyond the current team.

    Existing team effects can come from any reviewed source: another player,
    potion plan, set, skill, passive, or encounter assignment. Candidate effects
    are resolved through the same named-buff identity rules used by Extreme Build
    Lab so Comp Maker and Team Optimization do not grow a second stacking model.
    """

    @classmethod
    def evaluate(
        cls,
        *,
        existing_team_effects: tuple[NamedBuffContribution, ...] = (),
        candidate_effects: tuple[NamedBuffContribution, ...] = (),
    ) -> TeamProviderMarginalValue:
        baseline = NamedBuffResolutionService.resolve(existing_team_effects)
        combined = NamedBuffResolutionService.explain(
            tuple((*existing_team_effects, *candidate_effects))
        )

        baseline_by_identity = {
            (
                NamedBuffResolutionService.canonical_key(effect.stacking_key),
                str(effect.objective_key or "").strip(),
            ): effect
            for effect in baseline
        }
        candidate_ids = {id(effect) for effect in candidate_effects}

        marginal: list[NamedBuffContribution] = []
        for effect in combined.selected:
            if id(effect) not in candidate_ids:
                continue
            identity = (
                NamedBuffResolutionService.canonical_key(effect.stacking_key),
                str(effect.objective_key or "").strip(),
            )
            previous = baseline_by_identity.get(identity)
            if previous is None or float(effect.projected_delta) > float(previous.projected_delta) + 1e-9:
                marginal.append(effect)

        objectives = sorted(
            {
                str(effect.objective_key or "").strip()
                for effect in (*existing_team_effects, *candidate_effects)
                if str(effect.objective_key or "").strip()
            }
        )
        objective_deltas: list[tuple[str, float]] = []
        for objective in objectives:
            before, _ = NamedBuffResolutionService.score(
                existing_team_effects,
                objective_key=objective,
            )
            after, _ = NamedBuffResolutionService.score(
                tuple((*existing_team_effects, *candidate_effects)),
                objective_key=objective,
            )
            delta = after - before
            if abs(delta) > 1e-9:
                objective_deltas.append((objective, delta))

        suppressions = tuple(
            item
            for item in combined.suppressed
            if any(
                item.suppressed_source == effect.source
                or item.retained_source == effect.source
                for effect in candidate_effects
            )
        )
        return TeamProviderMarginalValue(
            marginal_effects=tuple(marginal),
            suppressed=suppressions,
            objective_deltas=tuple(objective_deltas),
        )
