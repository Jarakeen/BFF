from models.build_model import ChampionPointEntry, PlayerBuild

from minmax.saved_build_champion_point_slots import adapt_saved_champion_point_slots


def test_saved_cp_slots_become_canonical_allocations_without_deduping():
    build = PlayerBuild(
        ChampionPoints=[
            ChampionPointEntry(Name="Soothing Tide", Points="50"),
            ChampionPointEntry(Name="Breakfall", Points="50"),
            ChampionPointEntry(Name="Breakfall", Points="50"),
            ChampionPointEntry(),
        ]
    )

    result = adapt_saved_champion_point_slots(build)

    assert [(row.node_id, row.points) for row in result.allocations] == [
        ("soothing_tide", 50),
        ("breakfall", 50),
        ("breakfall", 50),
    ]
    assert result.unresolved == ()


def test_saved_cp_slots_report_malformed_entries_instead_of_guessing():
    build = PlayerBuild(
        ChampionPoints=[
            ChampionPointEntry(Name="Rejuvenator", Points="many"),
            ChampionPointEntry(Name="", Points="50"),
            ChampionPointEntry(Name="Swift Renewal", Points="-1"),
        ]
    )

    result = adapt_saved_champion_point_slots(build)

    assert result.allocations == ()
    assert len(result.unresolved) == 3
    assert "invalid points" in result.unresolved[0]
    assert "points but no node name" in result.unresolved[1]
    assert "negative points" in result.unresolved[2]
