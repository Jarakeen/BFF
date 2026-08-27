from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from services.build_catalog_service import BuildCatalogService


def test_same_character_can_have_multiple_builds(tmp_path: Path):
    roster = BuildRoster(
        Members=[
            PlayerBuild(Name="Alice", Gamertag="AliceGT", BuildName="Parse"),
            PlayerBuild(Name="Alice", Gamertag="AliceGT", BuildName="Lokkestiiz"),
        ]
    )

    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.import_legacy_roster(roster)

    assert len(catalog["characters"]) == 1
    assert len(catalog["builds"]) == 2
    assert {
        build["name"] for build in catalog["builds"]
    } == {"Parse", "Lokkestiiz"}
    assert {
        build["character_id"] for build in catalog["builds"]
    } == {catalog["characters"][0]["character_id"]}


def test_character_identity_prefers_gamertag(tmp_path: Path):
    roster = BuildRoster(
        Members=[
            PlayerBuild(Name="Alice", Gamertag="AliceGT", BuildName="Parse"),
            PlayerBuild(Name="Different Display Name", Gamertag="AliceGT", BuildName="Trial"),
        ]
    )

    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.import_legacy_roster(roster)

    assert len(catalog["characters"]) == 1
    assert len(catalog["builds"]) == 2
    assert catalog["characters"][0]["gamertag"] == "AliceGT"


def test_upsert_build_is_stable_for_same_character_and_name(tmp_path: Path):
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    catalog["characters"].append(
        {
            "character_id": "character_alice",
            "name": "Alice",
            "gamertag": "AliceGT",
        }
    )
    service.save(catalog)

    first = service.upsert_build(
        character_id="character_alice",
        build_name="Parse",
        payload={"BuildName": "Parse", "Food": "A"},
    )
    second = service.upsert_build(
        character_id="character_alice",
        build_name="Parse",
        payload={"BuildName": "Parse", "Food": "B"},
    )

    assert first["build_id"] == second["build_id"]
    assert len(service.builds_for_character("character_alice")) == 1
    assert service.get_build(first["build_id"])["payload"]["Food"] == "B"
