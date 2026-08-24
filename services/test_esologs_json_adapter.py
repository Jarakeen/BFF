"""
Focused tests for services/esologs_json_adapter.py.

These tests use a tiny synthetic fixture
(tests/fixtures/esologs_json_adapter_fixture.json) and never touch the
full data/raw/esologs_night2.json export. The integration test that
exercises the real 131,779-event file lives in
tests/test_esologs_json_adapter_integration.py and skips itself when
that file isn't present on disk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.esologs_event_interpreter import (
    EffectIntervalBuilder,
    SemanticEventKind,
)
from services.esologs_json_adapter import (
    EsoLogsJsonEventInterpreter,
    EsoLogsJsonFight,
    EsoLogsJsonFightNotFoundError,
    build_effect_intervals_from_json,
    load_semantic_events_from_json,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "esologs_json_adapter_fixture.json"
)


# ============================================================
# EsoLogsJsonFight loading
# ============================================================

def test_load_fight_reads_metadata() -> None:

    fight = EsoLogsJsonFight.load(FIXTURE_PATH, fight_id=6)

    assert fight.name == "Lokkestiiz"
    assert fight.encounter_id == 43
    assert fight.kill is True
    assert fight.start_time == 1000
    assert fight.end_time == 9000
    assert fight.report_code == "TESTCODE1"


def test_load_fight_event_count_matches_actual_events() -> None:

    fight = EsoLogsJsonFight.load(FIXTURE_PATH, fight_id=6)

    assert fight.declared_event_count == 9
    assert fight.event_count == len(fight.events)
    assert fight.event_count == 9


def test_load_selects_requested_fight_id() -> None:

    fight_six = EsoLogsJsonFight.load(FIXTURE_PATH, fight_id=6)
    fight_seven = EsoLogsJsonFight.load(FIXTURE_PATH, fight_id=7)

    assert fight_six.name == "Lokkestiiz"
    assert fight_seven.name == "Some Other Boss"
    assert fight_six.events != fight_seven.events


def test_missing_fight_id_raises() -> None:

    with pytest.raises(EsoLogsJsonFightNotFoundError):
        EsoLogsJsonFight.load(FIXTURE_PATH, fight_id=999)


# ============================================================
# Event translation -> SemanticCombatEvent
# ============================================================

def test_events_translate_to_semantic_combat_events() -> None:

    events = load_semantic_events_from_json(FIXTURE_PATH, fight_id=6)

    assert len(events) == 9

    kinds = [event.event_kind for event in events]

    assert kinds == [
        SemanticEventKind.CAST,
        SemanticEventKind.BUFF_APPLIED,
        SemanticEventKind.BUFF_REFRESHED,
        SemanticEventKind.BUFF_REMOVED,
        SemanticEventKind.DEBUFF_APPLIED,
        SemanticEventKind.DEBUFF_REMOVED,
        SemanticEventKind.DAMAGE,
        SemanticEventKind.RESOURCE_CHANGE,
        SemanticEventKind.UNKNOWN,
    ]


def test_timestamps_and_ids_are_preserved() -> None:

    events = load_semantic_events_from_json(FIXTURE_PATH, fight_id=6)

    cast_event = events[0]

    assert cast_event.timestamp == 1000
    assert cast_event.source_id == 1
    assert cast_event.target_id == 2
    assert cast_event.ability_game_id == 40223
    assert cast_event.ability_name == "Aggressive Horn"
    assert cast_event.fight_id == 6
    assert cast_event.report_code == "TESTCODE1"
    assert cast_event.event_index == 0


def test_raw_event_is_preserved_verbatim() -> None:

    events = load_semantic_events_from_json(FIXTURE_PATH, fight_id=6)

    damage_event = events[6]

    assert damage_event.raw_event["type"] == "damage"
    assert damage_event.raw_event["amount"] == 5432
    assert damage_event.raw_event["hitType"] == 2
    # Full raw dict retained, not just the fields we mapped.
    assert damage_event.raw_event == {
        "timestamp": 2000,
        "type": "damage",
        "sourceID": 1,
        "sourceIsFriendly": True,
        "targetID": 2,
        "targetIsFriendly": False,
        "abilityGameID": 40223,
        "amount": 5432,
        "hitType": 2,
    }


def test_unknown_raw_event_type_becomes_unknown_kind() -> None:

    events = load_semantic_events_from_json(FIXTURE_PATH, fight_id=6)

    unknown_event = events[-1]

    assert unknown_event.event_kind == SemanticEventKind.UNKNOWN
    assert unknown_event.raw_event_type == "some_future_event_type"


def test_no_game_mechanics_interpretation_leaks_in() -> None:
    """
    The adapter must not decide that an ability/event means something
    like Major Force. ability_name should only ever come from the raw
    event's own fields (abilityName / ability.name) or an explicitly
    supplied AbilityCatalog - never inferred from ability id alone.
    """

    events = load_semantic_events_from_json(FIXTURE_PATH, fight_id=6)

    buff_apply_event = events[1]

    # abilityGameID 61771 has no abilityName in the raw fixture and no
    # catalog was supplied, so the adapter must not invent a name.
    assert buff_apply_event.ability_game_id == 61771
    assert buff_apply_event.ability_name is None


# ============================================================
# Reuse of EffectIntervalBuilder
# ============================================================

def test_effect_interval_builder_is_reused_directly() -> None:

    fight = EsoLogsJsonFight.load(FIXTURE_PATH, fight_id=6)
    interpreter = EsoLogsJsonEventInterpreter(fight)

    # This is the exact class from esologs_event_interpreter.py - not a
    # reimplementation.
    builder = EffectIntervalBuilder(interpreter)

    intervals = builder.build(fight.report_code, fight.fight_id)

    assert len(intervals) == 2

    by_kind = {interval.effect_kind: interval for interval in intervals}

    buff_interval = by_kind["buff"]
    assert buff_interval.ability_game_id == 61771
    assert buff_interval.start_time == 1200
    assert buff_interval.end_time == 8000
    assert buff_interval.applications == 1
    assert buff_interval.refreshes == 1
    assert buff_interval.max_stack == 2
    assert buff_interval.confidence == "observed_remove"

    debuff_interval = by_kind["debuff"]
    assert debuff_interval.ability_game_id == 20802
    assert debuff_interval.start_time == 1500
    assert debuff_interval.end_time == 7000
    assert debuff_interval.applications == 1
    assert debuff_interval.refreshes == 0


def test_build_effect_intervals_from_json_convenience_function() -> None:

    intervals = build_effect_intervals_from_json(FIXTURE_PATH, fight_id=6)

    assert len(intervals) == 2
    assert {interval.effect_kind for interval in intervals} == {
        "buff",
        "debuff",
    }


def test_open_interval_when_no_remove_seen() -> None:
    """
    Fight 7's single cast event has no buff/debuff activity at all, so
    building intervals for it should yield nothing - and must not
    invent a fake expiration for anything.
    """

    intervals = build_effect_intervals_from_json(FIXTURE_PATH, fight_id=7)

    assert intervals == []


# ============================================================
# iter_fight duck-typing compatibility
# ============================================================

def test_iter_fight_supports_event_kind_filtering() -> None:

    fight = EsoLogsJsonFight.load(FIXTURE_PATH, fight_id=6)
    interpreter = EsoLogsJsonEventInterpreter(fight)

    damage_only = list(
        interpreter.iter_fight(
            fight.report_code,
            fight.fight_id,
            event_kinds={SemanticEventKind.DAMAGE},
        )
    )

    assert len(damage_only) == 1
    assert damage_only[0].event_kind == SemanticEventKind.DAMAGE


def test_iter_fight_supports_time_window_filtering() -> None:

    fight = EsoLogsJsonFight.load(FIXTURE_PATH, fight_id=6)
    interpreter = EsoLogsJsonEventInterpreter(fight)

    windowed = list(
        interpreter.iter_fight(
            fight.report_code,
            fight.fight_id,
            start_time=1000,
            end_time=2000,
        )
    )

    assert all(1000 <= event.timestamp <= 2000 for event in windowed)
    assert len(windowed) == 4
