from __future__ import annotations

import json
import sqlite3

from services.esologs_event_interpreter import (
    AbilityCatalog,
    EffectIntervalBuilder,
    EsoLogsEventInterpreter,
    SemanticEventKind,
)


def make_db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.execute(
        """
        CREATE TABLE log_event (
            report_code TEXT NOT NULL,
            fight_id INTEGER NOT NULL,
            event_index INTEGER NOT NULL,
            timestamp REAL NOT NULL,
            event_type TEXT NOT NULL,
            source_id INTEGER,
            source_is_friendly INTEGER,
            target_id INTEGER,
            target_instance INTEGER,
            target_is_friendly INTEGER,
            ability_game_id INTEGER,
            extra_ability_game_id INTEGER,
            amount REAL,
            hit_type INTEGER,
            tick INTEGER,
            cast_track_id INTEGER,
            resource_change REAL,
            resource_change_type INTEGER,
            other_resource_change REAL,
            max_resource_amount REAL,
            waste REAL,
            overheal REAL,
            absorbed REAL,
            stack INTEGER,
            raw_json TEXT NOT NULL,
            PRIMARY KEY (
                report_code,
                fight_id,
                event_index
            )
        )
        """
    )

    return connection


def insert_event(
    connection: sqlite3.Connection,
    *,
    index: int,
    timestamp: float,
    event_type: str,
    source_id: int = 1,
    target_id: int = 2,
    ability_id: int = 123,
    stack: int | None = None,
) -> None:

    raw = {
        "timestamp": timestamp,
        "type": event_type,
        "sourceID": source_id,
        "targetID": target_id,
        "abilityGameID": ability_id,
    }

    connection.execute(
        """
        INSERT INTO log_event (
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
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            "TEST",
            41,
            index,
            timestamp,
            event_type,
            source_id,
            1,
            target_id,
            None,
            1,
            ability_id,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            stack,
            json.dumps(raw),
        ),
    )

    connection.commit()


def test_event_classification() -> None:

    assert (
        EsoLogsEventInterpreter.classify_event("cast")
        == SemanticEventKind.CAST
    )

    assert (
        EsoLogsEventInterpreter.classify_event("applybuff")
        == SemanticEventKind.BUFF_APPLIED
    )

    assert (
        EsoLogsEventInterpreter.classify_event("refreshbuff")
        == SemanticEventKind.BUFF_REFRESHED
    )

    assert (
        EsoLogsEventInterpreter.classify_event("removebuff")
        == SemanticEventKind.BUFF_REMOVED
    )

    assert (
        EsoLogsEventInterpreter.classify_event("applydebuff")
        == SemanticEventKind.DEBUFF_APPLIED
    )

    assert (
        EsoLogsEventInterpreter.classify_event("damage")
        == SemanticEventKind.DAMAGE
    )

    assert (
        EsoLogsEventInterpreter.classify_event("heal")
        == SemanticEventKind.HEAL
    )

    assert (
        EsoLogsEventInterpreter.classify_event("death")
        == SemanticEventKind.DEATH
    )


def test_unknown_event_is_preserved() -> None:

    assert (
        EsoLogsEventInterpreter.classify_event("some_future_event")
        == SemanticEventKind.UNKNOWN
    )


def test_ability_catalog() -> None:

    catalog = AbilityCatalog(
        {
            40223: "Aggressive Horn",
        }
    )

    assert catalog.name_for(40223) == "Aggressive Horn"
    assert catalog.name_for(99999) is None


def test_interpreter_preserves_raw_event() -> None:

    connection = make_db()

    insert_event(
        connection,
        index=0,
        timestamp=1000,
        event_type="cast",
        ability_id=40223,
    )

    interpreter = EsoLogsEventInterpreter(
        connection,
        AbilityCatalog(
            {40223: "Aggressive Horn"}
        ),
    )

    events = list(
        interpreter.iter_fight(
            "TEST",
            41,
        )
    )

    assert len(events) == 1

    event = events[0]

    assert event.event_kind == SemanticEventKind.CAST
    assert event.ability_game_id == 40223
    assert event.ability_name == "Aggressive Horn"
    assert event.timestamp == 1000
    assert event.raw_event["type"] == "cast"


def test_effect_interval_apply_refresh_remove() -> None:

    connection = make_db()

    insert_event(
        connection,
        index=0,
        timestamp=1000,
        event_type="applybuff",
        ability_id=40223,
    )

    insert_event(
        connection,
        index=1,
        timestamp=4000,
        event_type="refreshbuff",
        ability_id=40223,
    )

    insert_event(
        connection,
        index=2,
        timestamp=9000,
        event_type="removebuff",
        ability_id=40223,
    )

    interpreter = EsoLogsEventInterpreter(
        connection,
        AbilityCatalog(
            {40223: "Aggressive Horn"}
        ),
    )

    builder = EffectIntervalBuilder(
        interpreter
    )

    intervals = builder.build(
        "TEST",
        41,
    )

    assert len(intervals) == 1

    interval = intervals[0]

    assert interval.start_time == 1000
    assert interval.end_time == 9000
    assert interval.applications == 1
    assert interval.refreshes == 1
    assert interval.ability_name == "Aggressive Horn"
    assert interval.confidence == "observed_remove"


def test_second_source_is_separate_interval() -> None:

    connection = make_db()

    # Source 1.
    insert_event(
        connection,
        index=0,
        timestamp=1000,
        event_type="applybuff",
        source_id=1,
        target_id=20,
        ability_id=40223,
    )

    insert_event(
        connection,
        index=1,
        timestamp=5000,
        event_type="removebuff",
        source_id=1,
        target_id=20,
        ability_id=40223,
    )

    # Source 2.
    insert_event(
        connection,
        index=2,
        timestamp=3000,
        event_type="applybuff",
        source_id=2,
        target_id=20,
        ability_id=40223,
    )

    insert_event(
        connection,
        index=3,
        timestamp=7000,
        event_type="removebuff",
        source_id=2,
        target_id=20,
        ability_id=40223,
    )

    interpreter = EsoLogsEventInterpreter(
        connection,
        AbilityCatalog(
            {40223: "Aggressive Horn"}
        ),
    )

    intervals = EffectIntervalBuilder(
        interpreter
    ).build(
        "TEST",
        41,
    )

    assert len(intervals) == 2

    assert {
        interval.source_id
        for interval in intervals
    } == {1, 2}


def test_open_interval_is_not_given_fake_expiration() -> None:

    connection = make_db()

    insert_event(
        connection,
        index=0,
        timestamp=1000,
        event_type="applybuff",
        ability_id=40223,
    )

    interpreter = EsoLogsEventInterpreter(
        connection,
        AbilityCatalog(
            {40223: "Aggressive Horn"}
        ),
    )

    intervals = EffectIntervalBuilder(
        interpreter
    ).build(
        "TEST",
        41,
    )

    assert len(intervals) == 1

    assert intervals[0].end_time is None
    assert intervals[0].confidence == "open_at_fight_end"