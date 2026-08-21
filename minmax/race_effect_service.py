from __future__ import annotations

from .effects import Effect, EffectKind, EffectOperation
from .race_repository import RaceRepository
from .stat_ids import StatId


class RaceEffectService:
    """Resolve structured racial stat bonuses into Effects."""

    def __init__(self, repository: RaceRepository):
        self.repository = repository

    def resolve_effects(self, race_id: int) -> list[Effect]:
        """Resolve all structured stat effects for a race."""

        race = self.repository.get_race_by_id(race_id)

        if race is None:
            return []

        effects: list[Effect] = []

        for racial_stat in self.repository.get_stats(race_id):
            try:
                stat = StatId(racial_stat.stat)
            except ValueError as exc:
                raise ValueError(
                    f"Unknown racial stat {racial_stat.stat!r} "
                    f"for race {race.name!r}"
                ) from exc

            effects.append(
                Effect(
                    operation=EffectOperation.ADD,
                    value=float(racial_stat.value),
                    source=f"{race.name} racial bonus",
                    stat=stat,
                    kind=EffectKind.STAT,
                )
            )

        return effects
    