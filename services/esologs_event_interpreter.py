from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from typing import Any, Iterable


# ============================================================
# Semantic event types
# ============================================================

CAST_EVENTS = {
    "cast",
    "begincast",
    "completecast",
}

BUFF_APPLY_EVENTS = {
    "applybuff",
    "applybuffstack",
}

BUFF_REFRESH_EVENTS = {
    "refreshbuff",
    "refreshbuffstack",
}

BUFF_REMOVE_EVENTS = {
    "removebuff",
    "removebuffstack",
}

DEBUFF_APPLY_EVENTS = {
    "applydebuff",
    "applydebuffstack",
}

DEBUFF_REFRESH_EVENTS = {
    "refreshdebuff",
    "refreshdebuffstack",
}

DEBUFF_REMOVE_EVENTS = {
    "removedebuff",
    "removedebuffstack",
}

DAMAGE_EVENTS = {
    "damage",
}

HEAL_EVENTS = {
    "heal",
    "hot",
}

DEATH_EVENTS = {
    "death",
}

RESOURCE_EVENTS = {
    "resourcechange",
}

ABSORB_EVENTS = {
    "absorbed",
}


# ============================================================
# Semantic categories
# ============================================================

class SemanticEventKind:
    CAST = "cast"

    BUFF_APPLIED = "buff_applied"
    BUFF_REFRESHED = "buff_refreshed"
    BUFF_REMOVED = "buff_removed"

    DEBUFF_APPLIED = "debuff_applied"
    DEBUFF_REFRESHED = "debuff_refreshed"
    DEBUFF_REMOVED = "debuff_removed"

    DAMAGE = "damage"
    HEAL = "heal"
    DEATH = "death"
    RESOURCE_CHANGE = "resource_change"
    ABSORB = "absorb"

    UNKNOWN = "unknown"


# ============================================================
# Normalized semantic event
# ============================================================

@dataclass(frozen=True)
class SemanticCombatEvent:
    report_code: str
    fight_id: int
    event_index: int

    timestamp: float
    event_kind: str

    source_id: int | None
    target_id: int | None

    ability_game_id: int | None
    extra_ability_game_id: int | None

    ability_name: str | None

    amount: float | None
    stack: int | None

    source_is_friendly: bool | None
    target_is_friendly: bool | None

    hit_type: int | None
    tick: bool | None

    cast_track_id: int | None

    resource_change: float | None
    resource_change_type: int | None
    other_resource_change: float | None
    max_resource_amount: float | None

    waste: float | None
    overheal: float | None
    absorbed: float | None

    # Original ESO Logs event type.
    raw_event_type: str

    # We retain the original event so nothing is lost.
    raw_event: dict[str, Any]


# ============================================================
# Ability catalog
# ============================================================

class AbilityCatalog:
    """
    Optional lookup layer.

    The interpreter does NOT require ability names to function.

    If a catalog is supplied, it can resolve:

        ability_game_id -> ability name

    This keeps the event interpreter independent of the ESO
    database while allowing names to be added later.
    """

    def __init__(
        self,
        abilities: dict[int, str] | None = None,
    ) -> None:
        self._abilities = abilities or {}

    def name_for(self, ability_id: int | None) -> str | None:
        if ability_id is None:
            return None

        return self._abilities.get(int(ability_id))

    @classmethod
    def from_json(
        cls,
        path: str,
    ) -> "AbilityCatalog":
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, dict):
            raise ValueError(
                f"Ability catalog must be a JSON object: {path}"
            )

        abilities: dict[int, str] = {}

        for key, value in payload.items():
            try:
                ability_id = int(key)
            except (TypeError, ValueError):
                continue

            if isinstance(value, str):
                abilities[ability_id] = value

        return cls(abilities)


# ============================================================
# Interpreter
# ============================================================

class EsoLogsEventInterpreter:
    """
    Convert raw ESO Logs events stored in log_event into
    stable semantic combat events.

    This class intentionally does NOT interpret encounter
    mechanics.

    Example:

        applybuff
            ->
        BUFF_APPLIED

    but it does NOT decide:

        "This means Major Force"

    That requires authoritative ability/effect data and
    belongs in the effect-resolution layer.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        ability_catalog: AbilityCatalog | None = None,
    ) -> None:
        self.connection = connection
        self.ability_catalog = ability_catalog or AbilityCatalog()

    # --------------------------------------------------------
    # Raw JSON
    # --------------------------------------------------------

    @staticmethod
    def _parse_raw_event(
        raw_json: str | None,
    ) -> dict[str, Any]:
        if not raw_json:
            return {}

        try:
            payload = json.loads(raw_json)
        except (TypeError, json.JSONDecodeError):
            return {}

        return payload if isinstance(payload, dict) else {}

    # --------------------------------------------------------
    # Event classification
    # --------------------------------------------------------

    @staticmethod
    def classify_event(
        raw_event_type: str,
    ) -> str:

        event_type = (
            str(raw_event_type or "")
            .strip()
            .lower()
        )

        if event_type in CAST_EVENTS:
            return SemanticEventKind.CAST

        if event_type in BUFF_APPLY_EVENTS:
            return SemanticEventKind.BUFF_APPLIED

        if event_type in BUFF_REFRESH_EVENTS:
            return SemanticEventKind.BUFF_REFRESHED

        if event_type in BUFF_REMOVE_EVENTS:
            return SemanticEventKind.BUFF_REMOVED

        if event_type in DEBUFF_APPLY_EVENTS:
            return SemanticEventKind.DEBUFF_APPLIED

        if event_type in DEBUFF_REFRESH_EVENTS:
            return SemanticEventKind.DEBUFF_REFRESHED

        if event_type in DEBUFF_REMOVE_EVENTS:
            return SemanticEventKind.DEBUFF_REMOVED

        if event_type in DAMAGE_EVENTS:
            return SemanticEventKind.DAMAGE

        if event_type in HEAL_EVENTS:
            return SemanticEventKind.HEAL

        if event_type in DEATH_EVENTS:
            return SemanticEventKind.DEATH

        if event_type in RESOURCE_EVENTS:
            return SemanticEventKind.RESOURCE_CHANGE

        if event_type in ABSORB_EVENTS:
            return SemanticEventKind.ABSORB

        return SemanticEventKind.UNKNOWN

    # --------------------------------------------------------
    # Database row -> semantic event
    # --------------------------------------------------------

    def interpret_row(
        self,
        row: sqlite3.Row,
    ) -> SemanticCombatEvent:

        raw_event_type = str(
            row["event_type"] or ""
        ).lower()

        ability_id = row["ability_game_id"]

        ability_name = (
            self.ability_catalog.name_for(
                ability_id
            )
        )

        # Some ESO Logs payloads may contain the ability
        # name even when the normalized DB field doesn't.
        raw_event = self._parse_raw_event(
            row["raw_json"]
        )

        if ability_name is None:
            ability_name = self._ability_name_from_raw(
                raw_event
            )

        return SemanticCombatEvent(
            report_code=row["report_code"],
            fight_id=int(row["fight_id"]),
            event_index=int(row["event_index"]),

            timestamp=float(row["timestamp"]),

            event_kind=self.classify_event(
                raw_event_type
            ),

            source_id=(
                int(row["source_id"])
                if row["source_id"] is not None
                else None
            ),

            target_id=(
                int(row["target_id"])
                if row["target_id"] is not None
                else None
            ),

            ability_game_id=(
                int(ability_id)
                if ability_id is not None
                else None
            ),

            extra_ability_game_id=(
                int(row["extra_ability_game_id"])
                if row["extra_ability_game_id"] is not None
                else None
            ),

            ability_name=ability_name,

            amount=self._float_or_none(
                row["amount"]
            ),

            stack=self._int_or_none(
                row["stack"]
            ),

            source_is_friendly=self._bool_or_none(
                row["source_is_friendly"]
            ),

            target_is_friendly=self._bool_or_none(
                row["target_is_friendly"]
            ),

            hit_type=self._int_or_none(
                row["hit_type"]
            ),

            tick=self._bool_or_none(
                row["tick"]
            ),

            cast_track_id=self._int_or_none(
                row["cast_track_id"]
            ),

            resource_change=self._float_or_none(
                row["resource_change"]
            ),

            resource_change_type=self._int_or_none(
                row["resource_change_type"]
            ),

            other_resource_change=self._float_or_none(
                row["other_resource_change"]
            ),

            max_resource_amount=self._float_or_none(
                row["max_resource_amount"]
            ),

            waste=self._float_or_none(
                row["waste"]
            ),

            overheal=self._float_or_none(
                row["overheal"]
            ),

            absorbed=self._float_or_none(
                row["absorbed"]
            ),

            raw_event_type=raw_event_type,

            raw_event=raw_event,
        )

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    @staticmethod
    def _float_or_none(
        value: Any,
    ) -> float | None:

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int_or_none(
        value: Any,
    ) -> int | None:

        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _bool_or_none(
        value: Any,
    ) -> bool | None:

        if value is None:
            return None

        return bool(value)

    @staticmethod
    def _ability_name_from_raw(
        raw_event: dict[str, Any],
    ) -> str | None:

        ability = raw_event.get("ability")

        if isinstance(ability, dict):
            name = ability.get("name")

            if isinstance(name, str):
                return name

        name = raw_event.get("abilityName")

        if isinstance(name, str):
            return name

        return None

    # --------------------------------------------------------
    # Iterate a fight
    # --------------------------------------------------------

    def iter_fight(
        self,
        report_code: str,
        fight_id: int,
        *,
        start_time: float | None = None,
        end_time: float | None = None,
        event_kinds: set[str] | None = None,
    ) -> Iterable[SemanticCombatEvent]:

        query = """
            SELECT
                report_code,
                fight_id,
                event_index,
                timestamp,
                event_type,
                source_id,
                source_is_friendly,
                target_id,
                target_instance,
                target_is_friendly,
                ability_game_id,
                extra_ability_game_id,
                amount,
                hit_type,
                tick,
                cast_track_id,
                resource_change,
                resource_change_type,
                other_resource_change,
                max_resource_amount,
                waste,
                overheal,
                absorbed,
                stack,
                raw_json
            FROM log_event
            WHERE report_code = ?
              AND fight_id = ?
        """

        params: list[Any] = [
            report_code,
            int(fight_id),
        ]

        if start_time is not None:
            query += """
                AND timestamp >= ?
            """
            params.append(float(start_time))

        if end_time is not None:
            query += """
                AND timestamp <= ?
            """
            params.append(float(end_time))

        query += """
            ORDER BY timestamp ASC, event_index ASC
        """

        cursor = self.connection.execute(
            query,
            params,
        )

        for row in cursor:
            event = self.interpret_row(row)

            if (
                event_kinds is not None
                and event.event_kind not in event_kinds
            ):
                continue

            yield event

    # --------------------------------------------------------
    # Convenience methods
    # --------------------------------------------------------

    def events_for_ability(
        self,
        report_code: str,
        fight_id: int,
        ability_game_id: int,
    ) -> list[SemanticCombatEvent]:

        return list(
            self._iter_ability(
                report_code,
                fight_id,
                ability_game_id,
            )
        )

    def _iter_ability(
        self,
        report_code: str,
        fight_id: int,
        ability_game_id: int,
    ) -> Iterable[SemanticCombatEvent]:

        rows = self.connection.execute(
            """
            SELECT
                report_code,
                fight_id,
                event_index,
                timestamp,
                event_type,
                source_id,
                source_is_friendly,
                target_id,
                target_instance,
                target_is_friendly,
                ability_game_id,
                extra_ability_game_id,
                amount,
                hit_type,
                tick,
                cast_track_id,
                resource_change,
                resource_change_type,
                other_resource_change,
                max_resource_amount,
                waste,
                overheal,
                absorbed,
                stack,
                raw_json
            FROM log_event
            WHERE report_code = ?
              AND fight_id = ?
              AND ability_game_id = ?
            ORDER BY timestamp ASC, event_index ASC
            """,
            (
                report_code,
                int(fight_id),
                int(ability_game_id),
            ),
        )

        for row in rows:
            yield self.interpret_row(row)


# ============================================================
# Semantic effect interval builder
# ============================================================

@dataclass(frozen=True)
class EffectInterval:
    """
    Represents the observed lifetime of one application of
    an aura/effect.

    This is NOT yet a game-mechanics interpretation.

    It is simply:

        apply -> refresh* -> remove

    for one source/target/ability combination.
    """

    report_code: str
    fight_id: int

    source_id: int | None
    target_id: int | None

    ability_game_id: int | None
    ability_name: str | None

    effect_kind: str

    start_time: float
    end_time: float | None

    applications: int
    refreshes: int

    max_stack: int | None

    confidence: str


class EffectIntervalBuilder:

    def __init__(
        self,
        interpreter: EsoLogsEventInterpreter,
    ) -> None:
        self.interpreter = interpreter

    def build(
        self,
        report_code: str,
        fight_id: int,
    ) -> list[EffectInterval]:

        events = self.interpreter.iter_fight(
            report_code,
            fight_id,
            event_kinds={
                SemanticEventKind.BUFF_APPLIED,
                SemanticEventKind.BUFF_REFRESHED,
                SemanticEventKind.BUFF_REMOVED,
                SemanticEventKind.DEBUFF_APPLIED,
                SemanticEventKind.DEBUFF_REFRESHED,
                SemanticEventKind.DEBUFF_REMOVED,
            },
        )

        active: dict[
            tuple[Any, ...],
            EffectIntervalBuilder._ActiveEffect
        ] = {}

        completed: list[EffectInterval] = []

        for event in events:

            key = (
                event.event_kind.startswith("debuff_"),
                event.source_id,
                event.target_id,
                event.ability_game_id,
            )

            is_debuff = key[0]

            if event.event_kind in {
                SemanticEventKind.BUFF_APPLIED,
                SemanticEventKind.DEBUFF_APPLIED,
            }:

                # If an apply arrives while an existing interval is
                # active, treat it as a refresh rather than inventing
                # simultaneous identical instances.
                if key in active:

                    current = active[key]

                    active[key] = current.with_refresh(
                        timestamp=event.timestamp,
                        stack=event.stack,
                    )

                else:

                    active[key] = self._ActiveEffect(
                        report_code=event.report_code,
                        fight_id=event.fight_id,
                        source_id=event.source_id,
                        target_id=event.target_id,
                        ability_game_id=event.ability_game_id,
                        ability_name=event.ability_name,
                        effect_kind=(
                            "debuff"
                            if is_debuff
                            else "buff"
                        ),
                        start_time=event.timestamp,
                        last_time=event.timestamp,
                        applications=1,
                        refreshes=0,
                        max_stack=event.stack,
                    )

            elif event.event_kind in {
                SemanticEventKind.BUFF_REFRESHED,
                SemanticEventKind.DEBUFF_REFRESHED,
            }:

                if key in active:

                    current = active[key]

                    active[key] = current.with_refresh(
                        timestamp=event.timestamp,
                        stack=event.stack,
                    )

            elif event.event_kind in {
                SemanticEventKind.BUFF_REMOVED,
                SemanticEventKind.DEBUFF_REMOVED,
            }:

                current = active.pop(key, None)

                if current is None:
                    continue

                completed.append(
                    current.finish(
                        event.timestamp
                    )
                )

        # Anything still active at the end of the fight gets
        # an open-ended interval. We do NOT invent an expiration.
        for current in active.values():
            completed.append(
                current.finish(None)
            )

        return completed

    @dataclass(frozen=True)
    class _ActiveEffect:

        report_code: str
        fight_id: int

        source_id: int | None
        target_id: int | None

        ability_game_id: int | None
        ability_name: str | None

        effect_kind: str

        start_time: float
        last_time: float

        applications: int
        refreshes: int

        max_stack: int | None

        def with_refresh(
            self,
            *,
            timestamp: float,
            stack: int | None,
        ) -> "EffectIntervalBuilder._ActiveEffect":

            max_stack = self.max_stack

            if stack is not None:
                if max_stack is None:
                    max_stack = stack
                else:
                    max_stack = max(
                        max_stack,
                        stack,
                    )

            return self.__class__(
                report_code=self.report_code,
                fight_id=self.fight_id,
                source_id=self.source_id,
                target_id=self.target_id,
                ability_game_id=self.ability_game_id,
                ability_name=self.ability_name,
                effect_kind=self.effect_kind,
                start_time=self.start_time,
                last_time=timestamp,
                applications=self.applications,
                refreshes=self.refreshes + 1,
                max_stack=max_stack,
            )

        def finish(
            self,
            timestamp: float | None,
        ) -> EffectInterval:

            return EffectInterval(
                report_code=self.report_code,
                fight_id=self.fight_id,
                source_id=self.source_id,
                target_id=self.target_id,
                ability_game_id=self.ability_game_id,
                ability_name=self.ability_name,
                effect_kind=self.effect_kind,
                start_time=self.start_time,
                end_time=timestamp,
                applications=self.applications,
                refreshes=self.refreshes,
                max_stack=self.max_stack,
                confidence=(
                    "observed_remove"
                    if timestamp is not None
                    else "open_at_fight_end"
                ),
            )


# ============================================================
# JSON export helper
# ============================================================

def semantic_events_to_json(
    events: Iterable[SemanticCombatEvent],
) -> list[dict[str, Any]]:

    return [
        asdict(event)
        for event in events
    ]


def effect_intervals_to_json(
    intervals: Iterable[EffectInterval],
) -> list[dict[str, Any]]:

    return [
        asdict(interval)
        for interval in intervals
    ]