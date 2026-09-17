from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .effects import Effect, EffectOperation, EffectUnit
from .stat_ids import StatId


U50_SOURCE_URL = "https://eso-hub.com/en/mundus-stones"
U51_SOURCE_URL = "https://hyperioxes.com/eso/news/update-51-pts-patch-notes"
U50_GAME_UPDATE = 50
U51_GAME_UPDATE = 51

# Update 50 live values, CP160. Unsupported character-sheet effects are kept in
# the DB deliberately so the calculator can report them instead of silently
# pretending they do not exist.
U50_MUNDUS_EFFECTS: dict[str, tuple[tuple[str, float, str, int, str], ...]] = {
    "The Apprentice": ((StatId.SPELL_DAMAGE.value, 238.0, "flat", 1, ""),),
    "The Atronach": ((StatId.MAGICKA_RECOVERY.value, 310.0, "flat", 1, ""),),
    "The Lady": (
        (StatId.PHYSICAL_RESISTANCE.value, 2744.0, "flat", 1, ""),
        (StatId.SPELL_RESISTANCE.value, 2744.0, "flat", 1, ""),
    ),
    "The Lord": ((StatId.MAX_HEALTH.value, 2225.0, "flat", 1, ""),),
    "The Lover": (
        (StatId.PHYSICAL_PENETRATION.value, 2744.0, "flat", 1, ""),
        (StatId.SPELL_PENETRATION.value, 2744.0, "flat", 1, ""),
    ),
    "The Mage": ((StatId.MAX_MAGICKA.value, 2023.0, "flat", 1, ""),),
    "The Ritual": ((StatId.HEALING_DONE.value, 8.0, "percent", 1, ""),),
    "The Serpent": ((StatId.STAMINA_RECOVERY.value, 310.0, "flat", 1, ""),),
    "The Shadow": (
        (StatId.CRITICAL_DAMAGE.value, 11.0, "percent", 1, ""),
        (StatId.CRITICAL_HEALING.value, 11.0, "percent", 1, ""),
    ),
    "The Steed": (
        (StatId.HEALTH_RECOVERY.value, 238.0, "flat", 1, ""),
        (StatId.MOVEMENT_SPEED.value, 10.0, "percent", 1, ""),
    ),
    "The Thief": ((StatId.CRITICAL_CHANCE.value, 1333.0, "rating", 1, ""),),
    "The Tower": ((StatId.MAX_STAMINA.value, 2023.0, "flat", 1, ""),),
    "The Warrior": ((StatId.WEAPON_DAMAGE.value, 238.0, "flat", 1, ""),),
}

# Update 51 PTS changes only the entries explicitly listed below. Values for
# unchanged stones inherit the U50 CP160 records. Apprentice's new progression
# bonuses are retained as unsupported records rather than being forced into the
# combat-stat layer.
U51_MUNDUS_EFFECTS: dict[str, tuple[tuple[str, float, str, int, str], ...]] = dict(U50_MUNDUS_EFFECTS)
U51_MUNDUS_EFFECTS.update(
    {
        "The Warrior": (
            (StatId.WEAPON_DAMAGE.value, 238.0, "flat", 1, ""),
            (StatId.SPELL_DAMAGE.value, 238.0, "flat", 1, ""),
        ),
        "The Apprentice": (
            (
                "experience_gain",
                8.0,
                "percent",
                0,
                "Update 51: 8% Experience gain is outside the combat character-sheet stat layer.",
            ),
            (
                "inspiration_gain",
                8.0,
                "percent",
                0,
                "Update 51: 8% Inspiration gain is outside the combat character-sheet stat layer.",
            ),
        ),
    }
)


def canonical_mundus_id(name: str, game_update: int) -> str:
    """Return a stable lower-snake-case identity for one update-versioned stone."""
    slug = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")
    return f"{slug}_u{int(game_update)}"


@dataclass(frozen=True)
class MundusEffectRecord:
    name: str
    stat_id: str
    value: float
    unit: str
    supported: bool
    notes: str = ""


class MundusRepository:
    """DB-backed, update-versioned Mundus Stone reference data.

    ``initialize=False`` is for calculation/audit paths that consume an already
    imported canonical database. It prevents a read-only calculation from
    rewriting the database merely because a repository object was constructed,
    and those repository connections are opened by SQLite in explicit read-only
    mode.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        game_update: int = U50_GAME_UPDATE,
        initialize: bool = True,
    ) -> None:
        self.database_path = str(database_path)
        self.game_update = int(game_update)
        self.read_only = not bool(initialize)
        self._names_cache: tuple[str, ...] | None = None
        self._records_cache: dict[str, tuple[MundusEffectRecord, ...]] = {}
        self._effects_cache: dict[
            tuple[str, float],
            tuple[tuple[Effect, ...], tuple[str, ...]],
        ] = {}
        if initialize:
            self.ensure_schema_and_seed()

    def _connect(self) -> sqlite3.Connection:
        if self.read_only:
            database_uri = Path(self.database_path).resolve().as_uri() + "?mode=ro"
            connection = sqlite3.connect(database_uri, uri=True)
            connection.execute("PRAGMA query_only = ON")
        else:
            connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
        return (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            ).fetchone()
            is not None
        )

    @staticmethod
    def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        if not MundusRepository._table_exists(connection, table_name):
            return set()
        return {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }

    @staticmethod
    def _create_canonical_tables(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS mundus_stone (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                game_update INTEGER NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                UNIQUE(name, game_update)
            );

            CREATE TABLE IF NOT EXISTS mundus_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mundus_id TEXT NOT NULL,
                stat_id TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                supported INTEGER NOT NULL DEFAULT 1,
                notes TEXT NOT NULL DEFAULT '',
                UNIQUE(mundus_id, stat_id),
                FOREIGN KEY (mundus_id) REFERENCES mundus_stone(id) ON DELETE CASCADE
            );
            """
        )

    def _migrate_legacy_schema(self, connection: sqlite3.Connection) -> None:
        """Migrate only Mundus tables to canonical text IDs without resetting the DB."""
        stone_columns = self._table_columns(connection, "mundus_stone")
        effect_columns = self._table_columns(connection, "mundus_effect")
        if not stone_columns and not effect_columns:
            self._create_canonical_tables(connection)
            return

        stone_id_type = ""
        if stone_columns:
            for row in connection.execute("PRAGMA table_info(mundus_stone)").fetchall():
                if row["name"] == "id":
                    stone_id_type = str(row["type"] or "").upper()
                    break

        already_canonical = (
            stone_columns
            and effect_columns
            and "id" in stone_columns
            and "mundus_id" in effect_columns
            and "TEXT" in stone_id_type
        )
        if already_canonical:
            return

        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            connection.execute("DROP TABLE IF EXISTS mundus_effect_new")
            connection.execute("DROP TABLE IF EXISTS mundus_stone_new")
            connection.executescript(
                """
                CREATE TABLE mundus_stone_new (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    game_update INTEGER NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    UNIQUE(name, game_update)
                );

                CREATE TABLE mundus_effect_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mundus_id TEXT NOT NULL,
                    stat_id TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    supported INTEGER NOT NULL DEFAULT 1,
                    notes TEXT NOT NULL DEFAULT '',
                    UNIQUE(mundus_id, stat_id),
                    FOREIGN KEY (mundus_id) REFERENCES mundus_stone_new(id) ON DELETE CASCADE
                );
                """
            )

            stone_id_map: dict[object, str] = {}
            if stone_columns:
                for row in connection.execute(
                    "SELECT id, name, game_update, source_url FROM mundus_stone"
                ).fetchall():
                    canonical_id = canonical_mundus_id(row["name"], row["game_update"])
                    stone_id_map[row["id"]] = canonical_id
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO mundus_stone_new(id, name, game_update, source_url)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            canonical_id,
                            row["name"],
                            int(row["game_update"]),
                            row["source_url"] or "",
                        ),
                    )

            legacy_fk_column = None
            if "mundus_id" in effect_columns:
                legacy_fk_column = "mundus_id"
            elif "mundus_stone_id" in effect_columns:
                legacy_fk_column = "mundus_stone_id"

            if effect_columns and legacy_fk_column:
                rows = connection.execute(
                    f"""
                    SELECT id, {legacy_fk_column} AS legacy_mundus_id,
                           stat_id, value, unit, supported, notes
                    FROM mundus_effect
                    ORDER BY id
                    """
                ).fetchall()
                for row in rows:
                    legacy_id = row["legacy_mundus_id"]
                    canonical_id = stone_id_map.get(legacy_id)
                    if canonical_id is None and isinstance(legacy_id, str):
                        canonical_id = legacy_id
                    if canonical_id is None:
                        continue
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO mundus_effect_new(
                            id, mundus_id, stat_id, value, unit, supported, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["id"],
                            canonical_id,
                            row["stat_id"],
                            row["value"],
                            row["unit"],
                            row["supported"],
                            row["notes"] or "",
                        ),
                    )

            if self._table_exists(connection, "mundus_effect"):
                connection.execute("DROP TABLE mundus_effect")
            if self._table_exists(connection, "mundus_stone"):
                connection.execute("DROP TABLE mundus_stone")
            connection.execute("ALTER TABLE mundus_stone_new RENAME TO mundus_stone")
            connection.execute("ALTER TABLE mundus_effect_new RENAME TO mundus_effect")
            connection.commit()
        finally:
            connection.execute("PRAGMA foreign_keys = ON")

    def ensure_schema_and_seed(self) -> None:
        with self._connect() as connection:
            self._migrate_legacy_schema(connection)
            self._create_canonical_tables(connection)
            source_url = U50_SOURCE_URL if self.game_update == U50_GAME_UPDATE else U51_SOURCE_URL
            effects = U50_MUNDUS_EFFECTS if self.game_update == U50_GAME_UPDATE else U51_MUNDUS_EFFECTS
            for name, rows in effects.items():
                mundus_id = canonical_mundus_id(name, self.game_update)
                connection.execute(
                    """
                    INSERT INTO mundus_stone(id, name, game_update, source_url)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        game_update = excluded.game_update,
                        source_url = excluded.source_url
                    """,
                    (mundus_id, name, self.game_update, source_url),
                )
                for stat_id, value, unit, supported, notes in rows:
                    connection.execute(
                        """
                        INSERT INTO mundus_effect(mundus_id, stat_id, value, unit, supported, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(mundus_id, stat_id) DO UPDATE SET
                            value = excluded.value,
                            unit = excluded.unit,
                            supported = excluded.supported,
                            notes = excluded.notes
                        """,
                        (mundus_id, stat_id, value, unit, supported, notes),
                    )
            connection.commit()

    def list_names(self) -> tuple[str, ...]:
        if self._names_cache is not None:
            return self._names_cache
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT name FROM mundus_stone WHERE game_update = ? ORDER BY name COLLATE NOCASE",
                (self.game_update,),
            ).fetchall()
        self._names_cache = tuple(row["name"] for row in rows)
        return self._names_cache

    def records_for_name(self, name: str) -> tuple[MundusEffectRecord, ...]:
        key = str(name or "").strip()
        if not key:
            return ()
        cached = self._records_cache.get(key.casefold())
        if cached is not None:
            return cached
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.name, e.stat_id, e.value, e.unit, e.supported, e.notes
                FROM mundus_stone AS s
                JOIN mundus_effect AS e ON e.mundus_id = s.id
                WHERE s.game_update = ? AND s.name = ? COLLATE NOCASE
                ORDER BY e.id
                """,
                (self.game_update, key),
            ).fetchall()
        result = tuple(
            MundusEffectRecord(
                name=row["name"],
                stat_id=row["stat_id"],
                value=float(row["value"]),
                unit=row["unit"],
                supported=bool(row["supported"]),
                notes=row["notes"] or "",
            )
            for row in rows
        )
        self._records_cache[key.casefold()] = result
        return result

    def get_effects(
        self,
        name: str,
        *,
        multiplier: float = 1.0,
    ) -> tuple[tuple[Effect, ...], tuple[str, ...]]:
        """Compatibility wrapper for the established public Mundus API."""
        return self.effects_for_name(
            name,
            divines_multiplier=multiplier,
        )

    def effects_for_name(
        self,
        name: str,
        *,
        divines_multiplier: float = 1.0,
    ) -> tuple[tuple[Effect, ...], tuple[str, ...]]:
        cache_key = (str(name or "").strip().casefold(), float(divines_multiplier))
        cached = self._effects_cache.get(cache_key)
        if cached is not None:
            return cached

        effects: list[Effect] = []
        unresolved: list[str] = []
        for record in self.records_for_name(name):
            if not record.supported:
                unresolved.append(f"{record.name}: {record.notes or record.stat_id}")
                continue
            try:
                stat = StatId(record.stat_id)
            except ValueError:
                unresolved.append(f"{record.name}: unsupported stat {record.stat_id}")
                continue
            value = float(record.value)
            if record.unit == "percent":
                value *= float(divines_multiplier)
                effects.append(
                    Effect(
                        stat=stat,
                        operation=EffectOperation.ADD_PERCENT,
                        value=value,
                        unit=EffectUnit.PERCENT,
                        source=f"Mundus: {record.name}",
                    )
                )
            elif record.unit == "rating":
                value *= float(divines_multiplier)
                effects.append(
                    Effect(
                        stat=stat,
                        operation=EffectOperation.ADD,
                        value=value,
                        unit=EffectUnit.RATING,
                        source=f"Mundus: {record.name}",
                    )
                )
            elif record.unit == "flat":
                effects.append(
                    Effect(
                        stat=stat,
                        operation=EffectOperation.ADD,
                        value=value,
                        unit=EffectUnit.FLAT,
                        source=f"Mundus: {record.name}",
                    )
                )
            else:
                unresolved.append(f"{record.name}: unsupported Mundus unit {record.unit}")

        result = (tuple(effects), tuple(unresolved))
        self._effects_cache[cache_key] = result
        return result
