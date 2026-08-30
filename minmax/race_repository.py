import sqlite3
from pathlib import Path

from .race import Race, RaceStat


class RaceRepository:
    """Read-only data access for races and structured racial stats.

    This layer exposes the race / race_stat tables as stored in the
    database. It does not interpret racial bonus text.
    """

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def get_race(self, name: str) -> Race | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    alliance,
                    association
                FROM race
                WHERE name = ?
                """,
                (name,),
            ).fetchone()

        if row is None:
            return None

        return self._to_race(row)

    def get_race_by_id(self, race_id: int) -> Race | None:
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    alliance,
                    association
                FROM race
                WHERE id = ?
                """,
                (race_id,),
            ).fetchone()

        if row is None:
            return None

        return self._to_race(row)

    def get_stats(self, race_id: int) -> list[RaceStat]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    race_id,
                    stat,
                    value
                FROM race_stat
                WHERE race_id = ?
                ORDER BY id
                """,
                (race_id,),
            ).fetchall()

        return [self._to_race_stat(row) for row in rows]

    def get_stat_map(self, race_id: int) -> dict[str, float]:
        """Return structured racial stat contributions keyed by StatId value."""
        return {stat.stat: float(stat.value) for stat in self.get_stats(race_id)}

    def get_stat_map_by_name(self, name: str) -> dict[str, float]:
        """Resolve a race by name and return its structured stat contributions."""
        race = self.get_race(name)
        if race is None:
            return {}
        return self.get_stat_map(race.id)

    @staticmethod
    def _to_race(row) -> Race:
        race_id, name, alliance, association = row

        return Race(
            id=race_id,
            name=name,
            alliance=alliance,
            association=association,
        )

    @staticmethod
    def _to_race_stat(row) -> RaceStat:
        stat_id, race_id, stat, value = row

        return RaceStat(
            id=stat_id,
            race_id=race_id,
            stat=stat,
            value=value,
        )
