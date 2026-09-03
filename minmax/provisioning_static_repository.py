from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from .effects import Effect, EffectOperation, EffectUnit
from .stat_ids import StatId


_COLOR = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
_NUMBER = r"([0-9]+(?:\.[0-9]+)?(?:-[0-9]+(?:\.[0-9]+)?)?)"


_PROVISIONING_NAME_ALIASES = {
    "clockwork citrus": "Clockwork Citrus Filet",
}


class ProvisioningStaticRepository:
    """Resolve long-duration food/drink character-sheet stats from eso.db.

    The repository intentionally understands both the canonical entity/source
    schema and older dedicated provisioning tables. This lets the calculation
    layer follow the database in use without creating a second food catalogue.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._list_names_cache: tuple[str, ...] | None = None
        self._description_cache: dict[str, str | None] = {}
        self._resolve_cache: dict[str, tuple[tuple[Effect, ...], tuple[str, ...]]] = {}

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _clean(text: str | None) -> str:
        return _COLOR.sub("", str(text or "")).strip()

    @staticmethod
    def canonical_name(name: str) -> str:
        selected = str(name or "").strip()
        return _PROVISIONING_NAME_ALIASES.get(selected.casefold(), selected)

    @staticmethod
    def _cp160_value(token: str) -> float:
        """Use the CP160 endpoint when an ESO tooltip stores a level range."""
        values = [float(part) for part in str(token).split("-") if part]
        return values[-1] if values else 0.0

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone() is not None

    @staticmethod
    def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
        return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}

    @staticmethod
    def _description_from_payload(data: dict) -> str | None:
        """Read tooltip text from raw or canonical processed provisioning JSON."""

        containers = [data]
        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            containers.append(metadata)

        raw_records = data.get("raw_records")
        if isinstance(raw_records, list):
            containers.extend(
                record for record in raw_records if isinstance(record, dict)
            )

        for container in containers:
            for key in (
                "abilityDesc",
                "ability_desc",
                "ability_description",
                "description",
                "effect_description",
            ):
                value = container.get(key)
                if value:
                    return str(value)
        return None

    def list_names(self) -> tuple[str, ...]:
        """Return deterministic provisioning names present in canonical data.

        This is a read-only catalogue view for bounded candidate enumeration. It
        intentionally does not claim that every listed tooltip is stat-mapped;
        callers that need evaluable foods still pass each name through ``resolve``.
        """
        if self._list_names_cache is not None:
            return self._list_names_cache

        names: dict[str, str] = {}
        with self._connect() as connection:
            if self._table_exists(connection, "entity"):
                for row in connection.execute(
                    """
                    SELECT DISTINCT name
                    FROM entity
                    WHERE entity_type IN ('food', 'drink', 'provisioning')
                      AND TRIM(COALESCE(name, '')) <> ''
                    """
                ).fetchall():
                    name = str(row["name"] or "").strip()
                    if name:
                        names.setdefault(name.casefold(), name)

            for table in ("food", "foods", "provisioning", "consumable"):
                if not self._table_exists(connection, table):
                    continue
                columns = self._columns(connection, table)
                if "name" not in columns:
                    continue
                for row in connection.execute(
                    f"SELECT DISTINCT name FROM {table} WHERE TRIM(COALESCE(name, '')) <> ''"
                ).fetchall():
                    name = str(row["name"] or "").strip()
                    if name:
                        names.setdefault(name.casefold(), name)

        self._list_names_cache = tuple(
            sorted(names.values(), key=lambda value: (value.casefold(), value))
        )
        return self._list_names_cache

    def _from_entity_source(self, connection: sqlite3.Connection, name: str) -> str | None:
        if not self._table_exists(connection, "entity") or not self._table_exists(connection, "entity_source"):
            return None
        rows = connection.execute(
            """
            SELECT es.raw_json
            FROM entity e
            JOIN entity_source es ON es.entity_id = e.id
            WHERE lower(e.name) = lower(?)
              AND e.entity_type IN ('food', 'drink', 'provisioning')
            ORDER BY es.id DESC
            """,
            (name,),
        ).fetchall()
        for row in rows:
            raw = str(row["raw_json"] or "").strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            description = self._description_from_payload(data)
            if description:
                return description
        return None

    def _from_dedicated_table(self, connection: sqlite3.Connection, name: str) -> str | None:
        for table in ("food", "foods", "provisioning", "consumable"):
            if not self._table_exists(connection, table):
                continue
            columns = self._columns(connection, table)
            if "name" not in columns:
                continue
            description_column = next(
                (candidate for candidate in ("ability_desc", "abilityDesc", "description", "effect_description", "raw_json") if candidate in columns),
                None,
            )
            if description_column is None:
                continue
            row = connection.execute(
                f"SELECT {description_column} AS value FROM {table} WHERE lower(name)=lower(?) LIMIT 1",
                (name,),
            ).fetchone()
            if row is None or not row["value"]:
                continue
            value = str(row["value"])
            if description_column == "raw_json":
                try:
                    data = json.loads(value)
                    value = str(
                        data.get("abilityDesc")
                        or data.get("ability_desc")
                        or data.get("description")
                        or ""
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
            if value.strip():
                return value
        return None

    def description(self, name: str) -> str | None:
        selected = self.canonical_name(name)
        if not selected:
            return None
        cache_key = selected.casefold()
        if cache_key in self._description_cache:
            return self._description_cache[cache_key]
        with self._connect() as connection:
            description = self._from_entity_source(connection, selected) or self._from_dedicated_table(connection, selected)
        self._description_cache[cache_key] = description
        return description

    @staticmethod
    def _effect(name: str, stat: StatId, value: float) -> Effect:
        return Effect(
            source=f"Food/Drink: {name}",
            stat=stat,
            operation=EffectOperation.ADD,
            value=float(value),
            unit=EffectUnit.FLAT,
        )

    def resolve(self, name: str) -> tuple[list[Effect], list[str]]:
        selected = self.canonical_name(name)
        if not selected:
            return [], []
        cache_key = selected.casefold()
        cached = self._resolve_cache.get(cache_key)
        if cached is not None:
            effects, unresolved = cached
            return list(effects), list(unresolved)

        description = self.description(selected)
        if not description:
            result = ((), (f"Food/Drink not found in canonical provisioning data: {selected}",))
            self._resolve_cache[cache_key] = result
            return [], list(result[1])

        text = self._clean(description)
        effects: list[Effect] = []

        stat_phrases = (
            ("Max Health", StatId.MAX_HEALTH),
            ("Max Magicka", StatId.MAX_MAGICKA),
            ("Max Stamina", StatId.MAX_STAMINA),
            ("Health Recovery", StatId.HEALTH_RECOVERY),
            ("Magicka Recovery", StatId.MAGICKA_RECOVERY),
            ("Stamina Recovery", StatId.STAMINA_RECOVERY),
        )

        # Common ESO tooltip grammar: one value shared by a list of stats.
        shared_patterns = (
            (rf"Increase Max Health, Magicka and Stamina by {_NUMBER}", (StatId.MAX_HEALTH, StatId.MAX_MAGICKA, StatId.MAX_STAMINA)),
            (rf"Increase Max Health and Magicka by {_NUMBER}", (StatId.MAX_HEALTH, StatId.MAX_MAGICKA)),
            (rf"Increase Max Health and Stamina by {_NUMBER}", (StatId.MAX_HEALTH, StatId.MAX_STAMINA)),
            (rf"Increase Max Magicka and Stamina by {_NUMBER}", (StatId.MAX_MAGICKA, StatId.MAX_STAMINA)),
            (rf"Increase Health, Magicka, and Stamina Recovery by {_NUMBER}", (StatId.HEALTH_RECOVERY, StatId.MAGICKA_RECOVERY, StatId.STAMINA_RECOVERY)),
            (rf"Increase Health Recovery by {_NUMBER} and Magicka and Stamina Recovery by {_NUMBER}", None),
        )
        consumed_spans: list[tuple[int, int]] = []
        for pattern, stats in shared_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            consumed_spans.append(match.span())
            if stats is None:
                health_value = self._cp160_value(match.group(1))
                shared_value = self._cp160_value(match.group(2))
                effects.append(self._effect(selected, StatId.HEALTH_RECOVERY, health_value))
                effects.append(self._effect(selected, StatId.MAGICKA_RECOVERY, shared_value))
                effects.append(self._effect(selected, StatId.STAMINA_RECOVERY, shared_value))
            else:
                value = self._cp160_value(match.group(1))
                effects.extend(self._effect(selected, stat, value) for stat in stats)

        def overlaps(span: tuple[int, int]) -> bool:
            return any(span[0] < used[1] and used[0] < span[1] for used in consumed_spans)

        # Mixed-value recipes use repeated "by X" clauses; resolve each one.
        for phrase, stat in stat_phrases:
            for match in re.finditer(rf"(?:Increase\s+)?{re.escape(phrase)} by {_NUMBER}", text, flags=re.IGNORECASE):
                if overlaps(match.span()):
                    continue
                effects.append(self._effect(selected, stat, self._cp160_value(match.group(1))))

        # Preserve one destination per stat even when a tooltip happens to match
        # both a broad and specific grammar form.
        deduped: dict[StatId, Effect] = {}
        for effect in effects:
            if effect.stat is not None:
                deduped[effect.stat] = effect
        if deduped:
            result = (tuple(deduped.values()), ())
            self._resolve_cache[cache_key] = result
            return list(result[0]), []

        result = ((), (f"Food/Drink has no mapped static character-sheet stats: {selected}: {text}",))
        self._resolve_cache[cache_key] = result
        return [], list(result[1])
