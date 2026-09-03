from models.build_model import ChampionPointEntry, PlayerBuild

from minmax.build_sustain_relevance import sustain_relevant_context_unresolved


def test_sustain_relevance_drops_unselected_dynamic_cp_and_explicit_non_sustain_boundaries() -> None:
    build = PlayerBuild(
        ChampionPoints=[ChampionPointEntry(Name="Swift Renewal", Points="50")]
    )

    result = sustain_relevant_context_unresolved(
        build,
        (
            "Champion Point is dynamic or not yet stat-mapped: Battle Mastery",
            "Potion selected; activation/uptime is not part of static build state: spell power",
            "Passive rank is not recorded for character: Frozen Armor",
            "The Steed: movement_speed unresolved (Movement speed is outside the current character-sheet stat layer.)",
        ),
    )

    assert result == ()


def test_sustain_relevance_keeps_selected_unmapped_cp_fail_closed() -> None:
    build = PlayerBuild(
        ChampionPoints=[ChampionPointEntry(Name="Battle Mastery", Points="50")]
    )

    result = sustain_relevant_context_unresolved(
        build,
        ("Champion Point is dynamic or not yet stat-mapped: BattleMastery",),
    )

    assert result == ("Champion Point is dynamic or not yet stat-mapped: BattleMastery",)


def test_sustain_relevance_keeps_unknown_recovery_passive_gap() -> None:
    build = PlayerBuild()

    result = sustain_relevant_context_unresolved(
        build,
        ("Passive rank is not recorded for character: Flourish",),
    )

    assert result == ("Passive rank is not recorded for character: Flourish",)
