from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from services.build_catalog_service import BuildCatalogService, SCHEMA_VERSION


def test_legacy_roster_migrates_to_one_character_per_identity(tmp_path: Path):
    roster = BuildRoster(
        Members=[
            PlayerBuild(Name="Alice", Gamertag="AliceGT", BuildName="Parse"),
            PlayerBuild(Name="Alice", Gamertag="AliceGT", BuildName="Lokkestiiz"),
            PlayerBuild(Name="Bob", Gamertag="BobGT", BuildName="Trial"),
        ]
    )

    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.import_legacy_roster(roster)

    assert catalog["schema_version"] == SCHEMA_VERSION
    assert len(catalog["characters"]) == 2
    assert len(catalog["builds"]) == 3

    alice = [c for c in catalog["characters"] if c["gamertag"] == "AliceGT"][0]
    alice_builds = service._normalize(catalog)["builds"]
    assert sum(b["character_id"] == alice["character_id"] for b in alice_builds) == 2


def test_blank_legacy_placeholder_is_not_migrated(tmp_path: Path):
    roster = BuildRoster(
        Members=[
            PlayerBuild(Name="Magrat", Gamertag="Jarakeen", BuildName="DF Healer"),
            PlayerBuild(),
        ]
    )

    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.import_legacy_roster(roster)

    assert len(catalog["characters"]) == 1
    assert len(catalog["builds"]) == 1
    assert catalog["characters"][0]["gamertag"] == "Jarakeen"
    assert catalog["builds"][0]["name"] == "DF Healer"


def test_catalog_round_trip_is_versioned(tmp_path: Path):
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    service.save(catalog)

    loaded = service.load()
    assert loaded == catalog
    assert loaded["schema_version"] == SCHEMA_VERSION


def test_delete_build_removes_only_named_build_and_preserves_identity(tmp_path) -> None:
    service = BuildCatalogService(tmp_path / "foundrydock.db")
    catalog = service.new_catalog()
    catalog["players"] = [
        {"player_id": "p1", "gamertag": "Rikbacon"},
        {"player_id": "p2", "gamertag": "Jarakeen"},
    ]
    catalog["characters"] = [
        {"character_id": "c1", "player_id": "p1", "name": "Bacon"},
        {
            "character_id": "c2",
            "player_id": "p2",
            "name": "Magrat",
            "passive_ranks": {"Bond With Nature": 2},
        },
    ]
    catalog["builds"] = [
        {"build_id": "b1", "character_id": "c1", "name": "Rik Tank", "payload": {}},
        {"build_id": "b2", "character_id": "c2", "name": "Jarakeen Healer", "payload": {}},
    ]
    service.save(catalog)

    assert service.delete_build("b1") is True

    after = service.load_strict()
    assert [row["build_id"] for row in after["builds"]] == ["b2"]
    assert {row["player_id"] for row in after["players"]} == {"p1", "p2"}
    assert {row["character_id"] for row in after["characters"]} == {"c1", "c2"}
    magrat = next(row for row in after["characters"] if row["character_id"] == "c2")
    assert magrat["passive_ranks"] == {"Bond With Nature": 2}


def test_delete_build_requires_stable_id_and_missing_id_is_noop(tmp_path) -> None:
    service = BuildCatalogService(tmp_path / "foundrydock.db")
    catalog = service.new_catalog()
    catalog["builds"] = [
        {"build_id": "b1", "character_id": "c1", "name": "Keep Me", "payload": {}},
    ]
    service.save(catalog)

    import pytest

    with pytest.raises(ValueError, match="build_id is required"):
        service.delete_build("")
    assert service.delete_build("does-not-exist") is False
    assert [row["build_id"] for row in service.load_strict()["builds"]] == ["b1"]
