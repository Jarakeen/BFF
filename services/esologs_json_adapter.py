"""
services/esologs_json_adapter.py

Adapter that reads a fight directly out of a raw ESO Logs JSON export
(e.g. research/raw/esologs_night2.json) and translates its events into the
EXISTING SemanticCombatEvent representation defined in
services/esologs_event_interpreter.py.

This module exists purely as an alternate *source* for that pipeline:

    sqlite log_event table  --\
                                >--  SemanticCombatEvent / EffectInterval
    raw ESO Logs JSON file  --/

It does not define a new event model, does not change
SemanticCombatEvent, EffectInterval, or EffectIntervalBuilder, and does
not add any game-mechanics interpretation (e.g. it never decides that
an ability/event means Major Force, Master's Architect, etc.). It only
performs the same *structural* classification the sqlite-backed
interpreter already performs (applybuff -> BUFF_APPLIED, and so on),
by reusing EsoLogsEventInterpreter.classify_event.

Expected raw JSON shape (as produced by the ESO Logs probe/export
tooling already used elsewhere in this project, e.g.
tools/extract_lokkestiiz_fight.py):

    {
      "report_code": "...",            # optional
      "fights": {
        "6": {
          "metadata": {
            "id": 6,
            "name": "Lokkestiiz",
            "encounterID": 43,
            "kill": true,
            "difficulty": ...,
            "startTime": ...,
            "endTime": ...,
            "bossPercentage": ...
          },
          "player_details": {...},
          "event_count": 131779,
          "events": [ {...}, {...}, ... ]
        }
      }
    }

Raw event fields follow the same ESO Logs camelCase convention already
relied on elsewhere in this project (services/esologs_raw_importer.py):
type, timestamp, sourceID, sourceIsFriendly, targetID, targetInstance,
targetIsFriendly, abilityGameID, extraAbilityGameID, amount, hitType,
tick, castTrackID, resourceChange, resourceChangeType,
otherResourceChange, maxResourceAmount, waste, overheal, absorbed,
stack.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from services.esologs_event_interpreter import (
    AbilityCatalog,
    EffectInterval,
    EffectIntervalBuilder,
    EsoLogsEventInterpreter,
    SemanticCombatEvent,
)

try:
    from services.paths import RAW_DATA

    DEFAULT_RAW_PATH = RAW_DATA / "esologs_night2.json"
except ImportError:  # pragma: no cover - paths module should always exist
    DEFAULT_RAW_PATH = Path("research/raw/esologs_night2.json")


# ============================================================
# Errors
# ============================================================

class EsoLogsJsonFightNotFoundError(KeyError):
    """Raised when the requested fight id is not present in the export."""


# ============================================================
# Raw JSON fight wrapper
# ============================================================

class EsoLogsJsonFight:
    """
    Thin, read-only wrapper around one fight entry from a raw ESO Logs
    JSON export.

    This class does no game-mechanics interpretation. It only exposes
    the raw structure (metadata + event list) so the interpreter layer
    below can translate it into SemanticCombatEvent objects.
    """

    def __init__(
        self,
        *,
        report_code: str,
        fight_id: int,
        metadata: dict[str, Any],
        events: list[dict[str, Any]],
        declared_event_count: int | None,
    ) -> None:
        self.report_code = report_code
        self.fight_id = fight_id
        self.metadata = metadata
        self.events = events
        self.declared_event_count = declared_event_count

    # --------------------------------------------------------
    # Metadata convenience accessors
    # --------------------------------------------------------

    @property
    def name(self) -> str | None:
        value = self.metadata.get("name")
        return value if isinstance(value, str) else None

    @property
    def encounter_id(self) -> int | None:
        value = self.metadata.get("encounterID")
        return int(value) if isinstance(value, (int, float)) else None

    @property
    def kill(self) -> bool | None:
        value = self.metadata.get("kill")
        return None if value is None else bool(value)

    @property
    def difficulty(self) -> Any:
        return self.metadata.get("difficulty")

    @property
    def start_time(self) -> float | None:
        value = self.metadata.get("startTime")
        return float(value) if isinstance(value, (int, float)) else None

    @property
    def end_time(self) -> float | None:
        value = self.metadata.get("endTime")
        return float(value) if isinstance(value, (int, float)) else None

    @property
    def event_count(self) -> int:
        """Actual number of parsed event dicts (ground truth)."""
        return len(self.events)

    # --------------------------------------------------------
    # Loading
    # --------------------------------------------------------

    @classmethod
    def load(
        cls,
        path: str | Path = DEFAULT_RAW_PATH,
        *,
        fight_id: int,
        report_code: str | None = None,
    ) -> "EsoLogsJsonFight":

        path = Path(path)

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        return cls.from_payload(
            payload,
            fight_id=fight_id,
            report_code=report_code,
            source_name=str(path),
        )

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        fight_id: int,
        report_code: str | None = None,
        source_name: str = "<in-memory>",
    ) -> "EsoLogsJsonFight":

        if not isinstance(payload, dict):
            raise ValueError(
                f"{source_name}: expected a JSON object at the top level"
            )

        fights = payload.get("fights")

        if not isinstance(fights, dict):
            raise ValueError(
                f"{source_name}: expected payload['fights'] to be an "
                f"object keyed by fight id"
            )

        key = str(fight_id)
        fight = fights.get(key)

        if not isinstance(fight, dict):
            raise EsoLogsJsonFightNotFoundError(
                f"Fight {fight_id!r} not found in {source_name}"
            )

        metadata = fight.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}

        raw_events = fight.get("events")
        events = (
            [event for event in raw_events if isinstance(event, dict)]
            if isinstance(raw_events, list)
            else []
        )

        declared_event_count = fight.get("event_count")
        declared_event_count = (
            int(declared_event_count)
            if isinstance(declared_event_count, (int, float))
            else None
        )

        resolved_report_code = (
            report_code
            or str(payload.get("report_code") or Path(source_name).stem)
        )

        return cls(
            report_code=resolved_report_code,
            fight_id=int(fight_id),
            metadata=metadata,
            events=events,
            declared_event_count=declared_event_count,
        )


# ============================================================
# Small local type-coercion helpers
# ============================================================
#
# Deliberately NOT reusing EsoLogsEventInterpreter's underscore-prefixed
# helpers here - those are private to that class. These are trivial
# type coercions, not game-mechanics interpretation, so duplicating
# them keeps this adapter decoupled from that class's internals while
# still reusing the one thing that actually matters: classify_event.

def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _ability_name_from_raw(raw_event: dict[str, Any]) -> str | None:
    ability = raw_event.get("ability")

    if isinstance(ability, dict):
        name = ability.get("name")

        if isinstance(name, str):
            return name

    name = raw_event.get("abilityName")

    if isinstance(name, str):
        return name

    return None


# ============================================================
# JSON -> SemanticCombatEvent interpreter
# ============================================================

class EsoLogsJsonEventInterpreter:
    """
    Translate raw ESO Logs JSON events (loaded directly from a probe
    export) into the EXISTING SemanticCombatEvent representation,
    without going through the sqlite-backed log_event table.

    Structural classification is delegated to
    EsoLogsEventInterpreter.classify_event, so "applybuff" -> BUFF_APPLIED
    etc. are defined in exactly one place. This class adds no
    game-mechanics interpretation of its own.

    It also exposes iter_fight(...) with the same signature as
    EsoLogsEventInterpreter.iter_fight, so an instance of this class can
    be handed directly to the existing EffectIntervalBuilder unchanged.
    """

    def __init__(
        self,
        fight: EsoLogsJsonFight,
        ability_catalog: AbilityCatalog | None = None,
    ) -> None:
        self.fight = fight
        self.ability_catalog = ability_catalog or AbilityCatalog()

    # --------------------------------------------------------
    # One raw event -> SemanticCombatEvent
    # --------------------------------------------------------

    def interpret_event(
        self,
        event_index: int,
        raw_event: dict[str, Any],
    ) -> SemanticCombatEvent:

        raw_event_type = str(raw_event.get("type") or "").lower()

        ability_id = raw_event.get("abilityGameID")

        ability_name = self.ability_catalog.name_for(ability_id)

        if ability_name is None:
            ability_name = _ability_name_from_raw(raw_event)

        return SemanticCombatEvent(
            report_code=self.fight.report_code,
            fight_id=self.fight.fight_id,
            event_index=event_index,

            timestamp=_float_or_none(raw_event.get("timestamp")) or 0.0,

            event_kind=EsoLogsEventInterpreter.classify_event(
                raw_event_type
            ),

            source_id=_int_or_none(raw_event.get("sourceID")),
            target_id=_int_or_none(raw_event.get("targetID")),

            ability_game_id=_int_or_none(ability_id),
            extra_ability_game_id=_int_or_none(
                raw_event.get("extraAbilityGameID")
            ),

            ability_name=ability_name,

            amount=_float_or_none(raw_event.get("amount")),
            stack=_int_or_none(raw_event.get("stack")),

            source_is_friendly=_bool_or_none(
                raw_event.get("sourceIsFriendly")
            ),
            target_is_friendly=_bool_or_none(
                raw_event.get("targetIsFriendly")
            ),

            hit_type=_int_or_none(raw_event.get("hitType")),
            tick=_bool_or_none(raw_event.get("tick")),

            cast_track_id=_int_or_none(raw_event.get("castTrackID")),

            resource_change=_float_or_none(
                raw_event.get("resourceChange")
            ),
            resource_change_type=_int_or_none(
                raw_event.get("resourceChangeType")
            ),
            other_resource_change=_float_or_none(
                raw_event.get("otherResourceChange")
            ),
            max_resource_amount=_float_or_none(
                raw_event.get("maxResourceAmount")
            ),

            waste=_float_or_none(raw_event.get("waste")),
            overheal=_float_or_none(raw_event.get("overheal")),
            absorbed=_float_or_none(raw_event.get("absorbed")),

            raw_event_type=raw_event_type,

            # The raw event is preserved verbatim (same dict that was
            # parsed from JSON - nothing is stripped or renamed).
            raw_event=raw_event,
        )

    # --------------------------------------------------------
    # All events, in file order
    # --------------------------------------------------------

    def iter_events(self) -> Iterable[SemanticCombatEvent]:
        for index, raw_event in enumerate(self.fight.events):
            yield self.interpret_event(index, raw_event)

    # --------------------------------------------------------
    # iter_fight: duck-type compatible with
    # EsoLogsEventInterpreter.iter_fight so this adapter can be passed
    # directly into EffectIntervalBuilder without modifying it.
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

        for event in self.iter_events():

            if start_time is not None and event.timestamp < start_time:
                continue

            if end_time is not None and event.timestamp > end_time:
                continue

            if (
                event_kinds is not None
                and event.event_kind not in event_kinds
            ):
                continue

            yield event


# ============================================================
# Convenience entry points
# ============================================================

def load_semantic_events_from_json(
    path: str | Path,
    fight_id: int,
    *,
    ability_catalog: AbilityCatalog | None = None,
    report_code: str | None = None,
) -> list[SemanticCombatEvent]:
    """
    Load one fight from a raw ESO Logs JSON export and return its
    events as a list of the existing SemanticCombatEvent objects.
    """

    fight = EsoLogsJsonFight.load(
        path,
        fight_id=fight_id,
        report_code=report_code,
    )

    interpreter = EsoLogsJsonEventInterpreter(fight, ability_catalog)

    return list(interpreter.iter_events())


def build_effect_intervals_from_json(
    path: str | Path,
    fight_id: int,
    *,
    ability_catalog: AbilityCatalog | None = None,
    report_code: str | None = None,
) -> list[EffectInterval]:
    """
    Load one fight from a raw ESO Logs JSON export and build
    EffectInterval objects for its buff/debuff apply/refresh/remove
    events, reusing the existing EffectIntervalBuilder unchanged.
    """

    fight = EsoLogsJsonFight.load(
        path,
        fight_id=fight_id,
        report_code=report_code,
    )

    interpreter = EsoLogsJsonEventInterpreter(fight, ability_catalog)

    builder = EffectIntervalBuilder(interpreter)  # type: ignore[arg-type]

    return builder.build(fight.report_code, fight.fight_id)
