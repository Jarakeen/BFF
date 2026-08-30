from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .effects import Effect, EffectOperation, EffectUnit
from .stat_ids import StatId


U50_SOURCE_URL = "https://eso-hub.com/en/mundus-stones"
U50_GAME_UPDATE = 50

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
        ("movement_speed", 10.0, "percent", 0, "Movement speed is outside the current character-sheet stat layer."),
    ),
    "The Thief": ((StatId.CRITICAL_CHANCE.value, 1333.0, "rating", 1, ""),),
    "The Tower": ((StatId.MAX_STAMINA.value, 2023.0, "flat", 1, ""),),
    "The Warrior": ((StatId.WEAPON_DAMAGE.value, 238.0, "flat", 1, ""),),
}


@dataclass(frozen=True)
class MundusEffectRecord:
    name: str
    stat_id: str
    value: float
    unit: str
    supported: bool
    notes: str = ""


class MundusRepository:
    """DB-backed, update-versioned Mundus Stone reference data."""

    def __init__(self, database_path: str | Path, *, game_update: int = U50_GAME_UPDATE) -> None:
        self.database_path = str(database_path)
        self.game_update = int(game_update)
        self.ensure_schema_and_seed()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def ensure_schema_and_seed(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS mundus_stone (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    game_update INTEGER NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    UNIQUE(name, game_update)
                );

                CREATE TABLE IF NOT EXISTS mundus_effect (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mundus_id INTEGER NOT NULL REFERENCES mundus_stone(id) ON DELETE CASCADE,
                    stat_id TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    supported INTEGER NOT NULL DEFAULT 1,
                    notes TEXT NOT NULL DEFAULT '',
                    UNIQUE(mundus_id, stat_id)
                );
                """
            )
            if self.game_update != U50_GAME_UPDATE:
                return

            for name, effects in U50_MUNDUS_EFFECTS.items():
                connection.execute(
                    """
                    INSERT INTO mundus_stone(name, game_update, source_url)
                    VALUES (?, ?, ?)
                    ON CONFLICT(name, game_update)
                    DO UPDATE SET source_url = excluded.source_url
                    """,
                    (name, U50_GAME_UPDATE, U50_SOURCE_URL),
                )
                row = connection.execute(
                    "SELECT id FROM mundus_stone WHERE name = ? AND game_update = ?",
                    (name, U50_GAME_UPDATE),
                ).fetchone()
                mundus_id = int(row["id"])
                for stat_id, value, unit, supported, notes in effects:
                    connection.execute(
                        """
                        INSERT INTO mundus_effect(mundus_id, stat_id, value, unit, supported, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(mundus_id, stat_id)
                        DO UPDATE SET
                            value = excluded.value,
                            unit = excluded.unit,
                            supported = excluded.supported,
                            notes = excluded.notes
                        """,
                        (mundus_id, stat_id, value, unit, supported, notes),
                    )

    def list_names(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT name FROM mundus_stone WHERE game_update = ? ORDER BY name",
                (self.game_update,),
            ).fetchall()
        return [str(row["name"]) for row in rows]

    def get_records(self, name: str) -> list[MundusEffectRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ms.name, me.stat_id, me.value, me.unit, me.supported, me.notes
                FROM mundus_stone ms
                JOIN mundus_effect me ON me.mundus_id = ms.id
                WHERE ms.name = ? AND ms.game_update = ?
                ORDER BY me.id
                """,
                (str(name).strip(), self.game_update),
            ).fetchall()
        return [
            MundusEffectRecord(
                name=str(row["name"]),
                stat_id=str(row["stat_id"]),
                value=float(row["value"]),
                unit=str(row["unit"]),
                supported=bool(row["supported"]),
                notes=str(row["notes"] or ""),
            )
            for row in rows
        ]

    def get_effects(self, name: str, *, multiplier: float = 1.0) -> tuple[list[Effect], list[str]]:
        effects: list[Effect] = []
        unresolved: list[str] = []
        for record in self.get_records(name):
            if not record.supported:
                unresolved.append(f"{record.name}: {record.stat_id} unresolved ({record.notes})")
                continue
            try:
                stat = StatId(record.stat_id)
            except ValueError:
                unresolved.append(f"{record.name}: unsupported stat {record.stat_id}")
                continue

            operation = EffectOperation.ADD_PERCENT if record.unit == "percent" else EffectOperation.ADD
            unit = EffectUnit.PERCENT if record.unit == "percent" else EffectUnit.FLAT
            effects.append(
                Effect(
                    source=f"Mundus: {record.name}",
                    stat=stat,
                    operation=operation,
                    value=float(record.value) * float(multiplier),
                    unit=unit,
                )
            )
        return effects, unresolved
