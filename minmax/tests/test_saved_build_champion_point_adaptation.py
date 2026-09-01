from pathlib import Path

from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from models.build_model import ChampionPointEntry, PlayerBuild


def _saved_build() -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        BuildName="CP Preservation",
        Race="",
        EsoClass="Warden",
        Role="Healer",
        ChampionPoints=[
            ChampionPointEntry(Name="Breakfall", Points="50"),
            ChampionPointEntry(Name="Breakfall", Points="50"),
            ChampionPointEntry(Name="Rejuvenation", Points="56"),
            ChampionPointEntry(Name="Boundless Vitality", Points="0"),
        ],
    )


def test_saved_champion_points_preserve_order_duplicates_and_points(tmp_path: Path):
    adapter = SavedBuildCharacterAdapter(tmp_path / "missing.db")

    result = adapter.adapt(_saved_build())

    assert result.build is not None
    assert tuple((entry.node_id, entry.points) for entry in result.build.champion_points) == (
        ("breakfall", 50),
        ("breakfall", 50),
        ("rejuvenation", 56),
        ("boundless_vitality", 0),
    )
    assert all(entry.effects == () for entry in result.build.champion_points)


def test_invalid_saved_champion_point_allocation_is_diagnostic(tmp_path: Path):
    saved = _saved_build()
    saved.ChampionPoints.append(ChampionPointEntry(Name="Celerity", Points="many"))
    adapter = SavedBuildCharacterAdapter(tmp_path / "missing.db")

    result = adapter.adapt(saved)

    assert result.build is not None
    assert len(result.build.champion_points) == 4
    assert any(
        "Champion Point entry 5 has invalid allocation: Celerity: many" in message
        for message in result.unresolved
    )


def test_negative_saved_champion_point_allocation_is_diagnostic(tmp_path: Path):
    saved = _saved_build()
    saved.ChampionPoints.append(ChampionPointEntry(Name="Celerity", Points="-1"))
    adapter = SavedBuildCharacterAdapter(tmp_path / "missing.db")

    result = adapter.adapt(saved)

    assert result.build is not None
    assert len(result.build.champion_points) == 4
    assert any(
        "Champion Point entry 5 has negative allocation: Celerity: -1" in message
        for message in result.unresolved
    )
