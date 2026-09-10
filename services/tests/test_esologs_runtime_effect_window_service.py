from minmax.runtime_effect_window import partition_runtime_effect_windows
from services.esologs_runtime_effect_window_service import EsoLogsRuntimeEffectWindowService


def test_explicit_apply_remove_builds_shared_runtime_window() -> None:
    result = EsoLogsRuntimeEffectWindowService().build(
        [
            {"timestamp": 1000.0, "sequence": 1, "type": "applybuff", "sourceID": 7, "targetID": 9, "abilityName": "Major Courage"},
            {"timestamp": 5000.0, "sequence": 2, "type": "removebuff", "sourceID": 7, "targetID": 9, "abilityName": "Major Courage"},
        ],
        fight_start_time_ms=0.0,
    )

    assert result.unresolved == ()
    assert len(result.windows) == 1
    window = result.windows[0]
    assert window.effect_name == "Major Courage"
    assert window.source == "esologs:actor:7"
    assert window.target == "esologs:actor:9"
    assert window.start_time_seconds == 1.0
    assert window.end_time_seconds == 5.0
    assert partition_runtime_effect_windows(result.windows, at_time_seconds=4.0).active == (window,)
    assert partition_runtime_effect_windows(result.windows, at_time_seconds=5.0).active == ()


def test_refresh_without_prior_apply_uses_refresh_as_earliest_defensible_start() -> None:
    result = EsoLogsRuntimeEffectWindowService().build(
        [
            {"timestamp": 3000.0, "type": "refreshdebuff", "sourceID": 7, "targetID": 99, "abilityName": "Major Brittle"},
            {"timestamp": 8000.0, "type": "removedebuff", "sourceID": 7, "targetID": 99, "abilityName": "Major Brittle"},
        ],
        fight_start_time_ms=1000.0,
    )

    assert result.unresolved == ()
    assert [(row.effect_name, row.start_time_seconds, row.end_time_seconds) for row in result.windows] == [
        ("Major Brittle", 2.0, 7.0)
    ]


def test_duplicate_open_fails_closed_without_replacing_prior_start() -> None:
    result = EsoLogsRuntimeEffectWindowService().build(
        [
            {"timestamp": 1000.0, "type": "applybuff", "sourceID": 1, "targetID": 2, "abilityName": "Example Buff"},
            {"timestamp": 2000.0, "type": "applybuff", "sourceID": 1, "targetID": 2, "abilityName": "Example Buff"},
            {"timestamp": 4000.0, "type": "removebuff", "sourceID": 1, "targetID": 2, "abilityName": "Example Buff"},
        ],
        fight_start_time_ms=0.0,
    )

    assert result.windows[0].start_time_seconds == 1.0
    assert result.windows[0].end_time_seconds == 4.0
    assert any("Duplicate open aura transition" in message for message in result.unresolved)


def test_open_without_observed_close_does_not_invent_window_end() -> None:
    result = EsoLogsRuntimeEffectWindowService().build(
        [
            {"timestamp": 1000.0, "type": "applybuff", "sourceID": 1, "targetID": 2, "abilityName": "Example Buff"},
        ],
        fight_start_time_ms=0.0,
    )

    assert result.windows == ()
    assert any("had no observed removal" in message for message in result.unresolved)


def test_remove_without_open_is_explicitly_unresolved() -> None:
    result = EsoLogsRuntimeEffectWindowService().build(
        [
            {"timestamp": 4000.0, "type": "removebuff", "sourceID": 1, "targetID": 2, "abilityName": "Example Buff"},
        ],
        fight_start_time_ms=0.0,
    )

    assert result.windows == ()
    assert any("had no observed open transition" in message for message in result.unresolved)


def test_numeric_ability_id_without_translated_name_is_not_promoted_to_effect_identity() -> None:
    result = EsoLogsRuntimeEffectWindowService().build(
        [
            {"timestamp": 1000.0, "type": "applydebuff", "sourceID": 1, "targetID": 99, "abilityGameID": 123456},
            {"timestamp": 3000.0, "type": "removedebuff", "sourceID": 1, "targetID": 99, "abilityGameID": 123456},
        ],
        fight_start_time_ms=0.0,
    )

    assert result.windows == ()
    assert result.unresolved == (
        "Aura transition with no translated ability name was not projected into runtime effect state.",
    )


def test_reviewed_effect_filter_ignores_unrelated_and_unnamed_auras() -> None:
    result = EsoLogsRuntimeEffectWindowService().build(
        [
            {"timestamp": 1000.0, "type": "applybuff", "sourceID": 7, "targetID": 9, "abilityName": "Wanted Effect"},
            {"timestamp": 1500.0, "type": "applybuff", "sourceID": 8, "targetID": 9, "abilityName": "Unrelated Effect"},
            {"timestamp": 1600.0, "type": "applybuff", "sourceID": 8, "targetID": 9, "abilityGameID": 555},
            {"timestamp": 3000.0, "type": "removebuff", "sourceID": 8, "targetID": 9, "abilityName": "Unrelated Effect"},
            {"timestamp": 4000.0, "type": "removebuff", "sourceID": 7, "targetID": 9, "abilityName": "Wanted Effect"},
        ],
        fight_start_time_ms=0.0,
        effect_names=("Wanted Effect",),
    )

    assert result.unresolved == ()
    assert [(row.effect_name, row.start_time_seconds, row.end_time_seconds) for row in result.windows] == [
        ("Wanted Effect", 1.0, 4.0)
    ]
