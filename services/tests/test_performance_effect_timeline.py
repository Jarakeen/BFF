from services.performance_effect_timeline import (
    EffectWindow,
    _effect_ids,
    build_effect_windows,
)


def test_effect_ids_keeps_only_named_support_effects() -> None:
    rows = [
        {"name": "Major Brittle", "guid": 145975},
        {"name": "Some Random Proc", "guid": 999},
        {"name": "Major Courage", "guid": "109966"},
    ]

    assert _effect_ids(rows) == {
        145975: "Major Brittle",
        109966: "Major Courage",
    }


def test_build_effect_windows_pairs_apply_refresh_and_remove() -> None:
    events = [
        {"timestamp": 101000, "type": "applydebuff", "abilityGameID": 145975, "targetID": 77},
        {"timestamp": 104000, "type": "refreshdebuff", "abilityGameID": 145975, "targetID": 77},
        {"timestamp": 109500, "type": "removedebuff", "abilityGameID": 145975, "targetID": 77},
    ]

    windows = build_effect_windows(
        events,
        id_to_name={145975: "Major Brittle"},
        fight_start_ms=100000,
        fight_end_ms=120000,
        source_label="Raid-Wide",
    )

    assert windows == [
        EffectWindow(
            Name="Major Brittle",
            StartSeconds=1.0,
            EndSeconds=9.5,
            Source="Raid-Wide",
            TargetId=77,
            AbilityId=145975,
            Confidence="observed_remove",
        )
    ]


def test_primary_target_keeps_enemy_with_most_coverage() -> None:
    events = [
        {"timestamp": 100000, "type": "applydebuff", "abilityGameID": 145975, "targetID": 10},
        {"timestamp": 118000, "type": "removedebuff", "abilityGameID": 145975, "targetID": 10},
        {"timestamp": 102000, "type": "applydebuff", "abilityGameID": 145975, "targetID": 20},
        {"timestamp": 106000, "type": "removedebuff", "abilityGameID": 145975, "targetID": 20},
    ]

    windows = build_effect_windows(
        events,
        id_to_name={145975: "Major Brittle"},
        fight_start_ms=100000,
        fight_end_ms=120000,
        source_label="Raid-Wide",
        choose_primary_target=True,
    )

    assert len(windows) == 1
    assert windows[0].TargetId == 10
    assert windows[0].StartSeconds == 0.0
    assert windows[0].EndSeconds == 18.0


def test_open_effect_is_clipped_to_fight_end() -> None:
    windows = build_effect_windows(
        [{"timestamp": 105000, "type": "applybuff", "abilityGameID": 109966, "targetID": 2}],
        id_to_name={109966: "Major Courage"},
        fight_start_ms=100000,
        fight_end_ms=120000,
        source_label="Your Buff",
    )

    assert windows[0].StartSeconds == 5.0
    assert windows[0].EndSeconds == 20.0
    assert windows[0].Confidence == "open_at_fight_end"
