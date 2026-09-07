from __future__ import annotations

"""Project canonical max-rank race stats into Extreme Build objective units.

The authoritative structured race source remains ``minmax.race_repository``.
The historical ``race_stat`` table is aggregate/max-rank data, which is useful
for Extreme race comparison, but it is not a complete model of every racial
passive or conditional racial mechanic.  This adapter therefore exposes only
those structured contributions and makes no completeness claim by itself.
"""

from dataclasses import dataclass

from minmax.race import Race, RaceStat
from minmax.race_repository import RaceRepository


@dataclass(frozen=True)
class ExtremeRaceObjectiveCandidate:
    race: Race
    objective_key: str
    projected_delta: float
    source_stats: tuple[RaceStat, ...]
    boundaries: tuple[str, ...] = ()

    @property
    def race_name(self) -> str:
        return self.race.name


class ExtremeRaceObjectiveService:
    """Enumerate structured max-rank race contributions for Extreme objectives."""

    REVIEWED_OBJECTIVES = (
        "critical_damage",
        "magicka_recovery",
        "stamina_recovery",
        "physical_resistance",
        "spell_resistance",
        "spell_damage",
        "weapon_damage",
        "spell_critical",
        "weapon_critical",
    )

    # ``race_stat`` currently stores only flat aggregate/max-rank stats.  Keys
    # outside this map remain a zero structured contribution, not proof that a
    # race has no relevant mechanic.  The coverage contract keeps race partial
    # until non-structured/conditional racial mechanics are reviewed as well.
    _STRUCTURED_STAT_BY_OBJECTIVE = {
        "magicka_recovery": "magicka_recovery",
        "stamina_recovery": "stamina_recovery",
        "physical_resistance": "physical_resistance",
        "spell_resistance": "spell_resistance",
        "spell_damage": "spell_damage",
        "weapon_damage": "weapon_damage",
    }

    _PARTIAL_BOUNDARY = (
        "Structured race_stat data is aggregate/max-rank and does not prove complete "
        "coverage of conditional or non-structured racial passive mechanics."
    )

    @classmethod
    def candidate_for_race(
        cls,
        repository: RaceRepository,
        race: Race,
        objective_key: str,
    ) -> ExtremeRaceObjectiveCandidate:
        objective = objective_key.strip().casefold()
        if objective not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme race objective: {objective_key!r}")

        expected_stat = cls._STRUCTURED_STAT_BY_OBJECTIVE.get(objective)
        stats = tuple(repository.get_stats(race.id))
        relevant = tuple(
            stat for stat in stats if expected_stat is not None and stat.stat == expected_stat
        )
        delta = sum(float(stat.value) for stat in relevant)

        return ExtremeRaceObjectiveCandidate(
            race=race,
            objective_key=objective,
            projected_delta=float(delta),
            source_stats=relevant,
            boundaries=(cls._PARTIAL_BOUNDARY,),
        )

    @classmethod
    def candidates_for_objective(
        cls,
        repository: RaceRepository,
        objective_key: str,
    ) -> tuple[ExtremeRaceObjectiveCandidate, ...]:
        rows = tuple(
            cls.candidate_for_race(repository, race, objective_key)
            for race in repository.list_races()
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    -row.projected_delta,
                    row.race_name.casefold(),
                    row.race.id,
                ),
            )
        )

    @classmethod
    def best_for_objective(
        cls,
        repository: RaceRepository,
        objective_key: str,
    ) -> ExtremeRaceObjectiveCandidate | None:
        rows = cls.candidates_for_objective(repository, objective_key)
        return rows[0] if rows else None
