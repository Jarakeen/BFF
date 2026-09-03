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
        # Instance-scoped caches preserve one canonical DB snapshot for the
        # repository lifetime while allowing a fresh repository to observe
        # later database changes.
        self._race_by_name_cache: dict[str, Race | None] = {}
        self._race_by_id_cache: dict[int, Race | None] = {}
        self._stats_cache: dict[int, tuple[RaceStat, ...]] = {}
        self._stat_map_cache: dict[int, dict[str, float]] = {}

    def get_race(self, name: str) -> Race | None:
        key = str(name)
        if key in self._race_by_name_cache:
            return self._race_by_name_cache[key]

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

        result = None if row is None else self._to_race(row)
        self._race_by_name_cache[key] = result
        if result is not None:
            self._race_by_id_cache.setdefault(int(result.id), result)
        return result

    def get_race_by_id(self, race_id: int) -> Race | None:
        key = int(race_id)
        if key in self._race_by_id_cache:
            return self._race_by_id_cache[key]

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

        result = None if row is None else self._to_race(row)
        self._race_by_id_cache[key] = result
        if result is not None:
            self._race_by_name_cache.setdefault(str(result.name), result)
        return result

    def get_stats(self, race_id: int) -> list[RaceStat]:
        key = int(race_id)
        cached = self._stats_cache.get(key)
        if cached is not None:
            return list(cached)

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

        result = tuple(self._to_race_stat(row) for row in rows)
        self._stats_cache[key] = result
        return list(result)

    def get_stat_map(self, race_id: int) -> dict[str, float]:
        """Return structured racial stat contributions keyed by StatId value."""
        key = int(race_id)
        cached = self._stat_map_cache.get(key)
        if cached is None:
            cached = {stat.stat: float(stat.value) for stat in self.get_stats(race_id)}
            self._stat_map_cache[key] = cached
        return dict(cached)

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
