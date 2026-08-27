from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from services.build_catalog_service import BuildCatalogService


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

    assert catalog["schema_version"] == 2
    assert len(catalog["characters"]) == 2
    assert len(catalog["builds"]) == 3

    alice = [c for c in catalog["characters"] if c["gamertag"] == "AliceGT"][0]
    alice_builds = service._normalize(catalog)["builds"]
    assert sum(b["character_id"] == alice["character_id"] for b in alice_builds) == 2


def test_blank_legacy_placeholder_is_not_migrated():
    roster = BuildRoster(
        Members=[
            PlayerBuild(Name="Alice", Gamertag="AliceGT", BuildName="Parse"),
            PlayerBuild(),
        ]
    )

    service = BuildCatalogService(Path("characters.json"))
    catalog = service.import_legacy_roster(roster)

    assert len(catalog["characters"]) == 1
    assert len(catalog["builds"]) == 1
    assert catalog["characters"][0]["gamertag"] == "AliceGT"
    assert catalog["builds"][0]["name"] == "Parse"


def test_catalog_round_trip_is_versioned(tmp_path: Path):
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    service.save(catalog)

    loaded = service.load()
    assert loaded == catalog
    assert loaded["schema_version"] == 2
