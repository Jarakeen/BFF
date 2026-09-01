from __future__ import annotations

from dataclasses import replace

from .character_progression import CharacterProgression
from .context_factory import BuildCalculationContextFactory
from .racial_passive_stat_repository import RacialPassiveStatRepository


class Phase5BuildCalculationContextFactory(BuildCalculationContextFactory):
    """Canonical Phase 5 context factory with explicit progression ownership.

    Legacy callers without individual passive progression retain the historical
    aggregate ``race_stat`` behavior. Canonical callers resolve racial stats
    from the exact purchased passive rank stored in character progression and
    the corresponding canonical ability tooltip in ``eso.db``.
    """

    def __init__(self, *args, racial_passive_repository=None, **kwargs):
        super().__init__(*args, **kwargs)
        database_path = getattr(self.race_repository, "database_path", None)
        self.racial_passive_repository = racial_passive_repository or (
            RacialPassiveStatRepository(database_path) if database_path else None
        )
        self._phase5_progression = None
        self._phase5_racial_messages: tuple[str, ...] = ()

    def build(self, *, progression: CharacterProgression, build, **kwargs):
        self._phase5_progression = progression
        self._phase5_racial_messages = ()
        try:
            context = super().build(progression=progression, build=build, **kwargs)
            if self._phase5_racial_messages:
                context = replace(
                    context,
                    unresolved_gear_effects=context.unresolved_gear_effects
                    + tuple(
                        message
                        for message in self._phase5_racial_messages
                        if message not in context.unresolved_gear_effects
                    ),
                )
            return context
        finally:
            self._phase5_progression = None
            self._phase5_racial_messages = ()

    def _race_stats(self, race_name: str) -> dict[str, float]:
        progression = self._phase5_progression
        if progression is None or progression.passive_ranks is None:
            return super()._race_stats(race_name)

        race = str(race_name or "").strip()
        if not race:
            return {}
        if self.racial_passive_repository is None:
            self._phase5_racial_messages = (
                f"Canonical racial passive resolver is unavailable: {race}",
            )
            return {}

        resolution = self.racial_passive_repository.resolve(race, progression)
        self._phase5_racial_messages = resolution.boundaries + resolution.unresolved
        return dict(resolution.stats)
