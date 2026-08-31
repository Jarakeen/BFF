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


def test_same_gamertag_can_have_multiple_characters(tmp_path: Path):
    roster = BuildRoster(
        Members=[
            PlayerBuild(Name="Alice", Gamertag="AliceGT", BuildName="Parse"),
            PlayerBuild(Name="Different Character", Gamertag="AliceGT", BuildName="Trial"),
        ]
    )

    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.import_legacy_roster(roster)

    assert len(catalog["characters"]) == 2
    assert len(catalog["builds"]) == 2
    assert {character["name"] for character in catalog["characters"]} == {
        "Alice",
        "Different Character",
    }
    assert {character["gamertag"] for character in catalog["characters"]} == {
        "AliceGT"
    }
    assert len({build["character_id"] for build in catalog["builds"]}) == 2


def test_existing_character_id_is_preserved_for_same_account_and_character(tmp_path: Path):
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    catalog["characters"].append(
        {
            "character_id": "existing-character-id",
            "name": "Alice",
            "gamertag": "AliceGT",
            "owned_skill_lines": [],
        }
    )
    service.save(catalog)

    imported = service.import_legacy_roster(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Alice",
                    Gamertag="AliceGT",
                    BuildName="Healer",
                )
            ]
        )
    )

    assert len(imported["characters"]) == 1
    assert imported["characters"][0]["character_id"] == "existing-character-id"
    assert imported["builds"][0]["character_id"] == "existing-character-id"


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


def test_legacy_character_defaults_to_no_explicit_owned_skill_lines(tmp_path: Path):
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    catalog["characters"].append(
        {
            "character_id": "character_alice",
            "name": "Alice",
            "eso_class": "Warden",
        }
    )
    service.save(catalog)

    character = service.get_character("character_alice")

    assert character is not None
    assert character["owned_skill_lines"] == []


def test_set_owned_skill_lines_is_character_scoped_and_duplicate_free(tmp_path: Path):
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    catalog["characters"].append(
        {
            "character_id": "character_alice",
            "name": "Alice",
            "eso_class": "Warden",
        }
    )
    service.save(catalog)

    updated = service.set_owned_skill_lines(
        character_id="character_alice",
        owned_skill_lines=[
            "Undaunted",
            "Mages Guild",
            "undaunted",
            "  Psijic Order  ",
            "",
        ],
    )

    assert updated is not None
    assert updated["owned_skill_lines"] == ["Undaunted", "Mages Guild", "Psijic Order"]
    assert service.get_character("character_alice")["owned_skill_lines"] == [
        "Undaunted",
        "Mages Guild",
        "Psijic Order",
    ]


def test_updating_owned_skill_lines_does_not_modify_build_payloads(tmp_path: Path):
    service = BuildCatalogService(tmp_path / "characters.json")
    catalog = service.new_catalog()
    catalog["characters"].append(
        {
            "character_id": "character_alice",
            "name": "Alice",
            "eso_class": "Warden",
        }
    )
    service.save(catalog)
    build = service.upsert_build(
        character_id="character_alice",
        build_name="Healer",
        payload={"BuildName": "Healer", "Mundus": "The Ritual"},
    )

    service.set_owned_skill_lines(
        character_id="character_alice",
        owned_skill_lines=["Undaunted", "Support"],
    )

    assert service.get_build(build["build_id"])["payload"] == {
        "BuildName": "Healer",
        "Mundus": "The Ritual",
    }


def test_legacy_resync_preserves_existing_owned_skill_lines(tmp_path: Path):
    service = BuildCatalogService(tmp_path / "characters.json")
    initial = service.import_legacy_roster(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Alice",
                    Gamertag="AliceGT",
                    BuildName="Healer",
                    EsoClass="Warden",
                )
            ]
        )
    )
    service.save(initial)
    character_id = initial["characters"][0]["character_id"]

    service.set_owned_skill_lines(
        character_id=character_id,
        owned_skill_lines=["Undaunted", "Psijic Order"],
    )

    resynced = service.import_legacy_roster(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Alice",
                    Gamertag="AliceGT",
                    BuildName="Healer",
                    EsoClass="Warden",
                    Mundus="The Ritual",
                )
            ]
        )
    )

    assert resynced["characters"][0]["character_id"] == character_id
    assert resynced["characters"][0]["owned_skill_lines"] == [
        "Undaunted",
        "Psijic Order",
    ]
