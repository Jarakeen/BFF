from __future__ import annotations

from dataclasses import replace

from .character_progression import CharacterProgression
from .context_factory import BuildCalculationContextFactory


class Phase5BuildCalculationContextFactory(BuildCalculationContextFactory):
    """Canonical Phase 5 context factory with explicit progression ownership.

    The legacy ``race_stat`` table stores aggregate max-rank racial bonuses and
    does not identify which individual purchased racial passive produced each
    stat. Canonical character progression therefore must not receive that whole
    package merely because a race is selected.

    Legacy callers that do not supply an individual passive map retain the old
    aggregate behavior for compatibility. Canonical callers with explicit
    passive progression fail closed until racial passive formulas/provenance are
    modeled individually.
    """

    RACIAL_AGGREGATE_PREFIX = (
        "Racial aggregate stats are not applied because individual racial passive "
        "ownership cannot be resolved from canonical data:"
    )

    def build(self, *, progression: CharacterProgression, build, **kwargs):
        self._phase5_progression = progression
        try:
            context = super().build(progression=progression, build=build, **kwargs)
        finally:
            self._phase5_progression = None

        race_name = str(getattr(build, "Race", "") or "").strip()
        if (
            race_name
            and progression.passive_ranks is not None
            and self.race_repository is not None
            and self.race_repository.get_stat_map_by_name(race_name)
        ):
            message = f"{self.RACIAL_AGGREGATE_PREFIX} {race_name}"
            if message not in context.unresolved_gear_effects:
                context = replace(
                    context,
                    unresolved_gear_effects=context.unresolved_gear_effects + (message,),
                )
        return context

    def _race_stats(self, race_name: str) -> dict[str, float]:
        progression = getattr(self, "_phase5_progression", None)
        if progression is not None and progression.passive_ranks is not None:
            return {}
        return super()._race_stats(race_name)
