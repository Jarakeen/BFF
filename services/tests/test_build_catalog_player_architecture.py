from __future__ import annotations

import json

from models.build_model import BuildRoster, PlayerBuild
from services.build_catalog_service import BuildCatalogService, SCHEMA_VERSION


def test_one_player_can_own_multiple_characters_and_builds(tmp_path) -> None:
    service = BuildCatalogService(tmp_path / "characters.json")
    roster = BuildRoster(
        Members=[
            PlayerBuild(
                Gamertag="Jarakeen",
                Name="Magrat",
                BuildName="DF Healer",
                EsoClass="Warden",
                Role="Healer",
                Mundus="The Ritual",
            ),
            PlayerBuild(
                Gamertag="Jarakeen",
                Name="Magrat",
                BuildName="RoJo Healer",
                EsoClass="Warden",
                Role="Healer",
                Mundus="The Atronach",
            ),
            PlayerBuild(
                Gamertag="Jarakeen",
                Name="Alt Healer",
                BuildName="Trial Healer",
                EsoClass="Templar",
                Role="Healer",
                Mundus="The Ritual",
            ),
        ]
    )

    catalog = service.import_legacy_roster(roster)
    service.save(catalog)
    catalog = service.load()

    assert catalog["schema_version"] == SCHEMA_VERSION
    assert len(catalog["players"]) == 1
    assert catalog["players"][0]["gamertag"] == "Jarakeen"

    player_id = catalog["players"][0]["player_id"]
    characters = service.characters_for_player(player_id)
    assert {character["name"] for character in characters} == {"Magrat", "Alt Healer"}

    magrat = next(character for character in characters if character["name"] == "Magrat")
    builds = service.builds_for_character(magrat["character_id"])
    assert {build["name"] for build in builds} == {"DF Healer", "RoJo Healer"}


def test_multiple_players_with_multiple_characters_do_not_collapse(tmp_path) -> None:
    service = BuildCatalogService(tmp_path / "characters.json")
    roster = BuildRoster(
        Members=[
            PlayerBuild(Gamertag="Jarakeen", Name="Magrat", BuildName="DF Healer", Role="Healer"),
            PlayerBuild(Gamertag="N1njaBoyRylo", Name="Arc DD", BuildName="Parse", Role="Damage Dealer"),
            PlayerBuild(Gamertag="N1njaBoyRylo", Name="Templar DD", BuildName="Trial", Role="Damage Dealer"),
        ]
    )

    service.save(service.import_legacy_roster(roster))
    players = service.list_players()

    assert {player["gamertag"] for player in players} == {"Jarakeen", "N1njaBoyRylo"}
    rylo = next(player for player in players if player["gamertag"] == "N1njaBoyRylo")
    assert {character["name"] for character in service.characters_for_player(rylo["player_id"])} == {
        "Arc DD",
        "Templar DD",
    }


def test_build_can_have_multiple_team_assignments_without_identity_duplication(tmp_path) -> None:
    service = BuildCatalogService(tmp_path / "characters.json")
    roster = BuildRoster(
        Members=[
            PlayerBuild(
                Gamertag="Jarakeen",
                Name="Magrat",
                BuildName="DF Healer",
                Role="Healer",
                Mundus="The Ritual",
            )
        ]
    )
    service.save(service.import_legacy_roster(roster))
    build = service.load()["builds"][0]

    service.assign_build_to_team(
        build_id=build["build_id"],
        team_name="Performance Mode",
        raid_role="Healer",
        slot_name="Group Healer",
    )
    service.assign_build_to_team(
        build_id=build["build_id"],
        team_name="HH",
        raid_role="Healer",
        slot_name="Healer 2",
    )

    assignments = service.assignments_for_build(build["build_id"])
    assert {assignment["team_name"] for assignment in assignments} == {"Performance Mode", "HH"}
    assert len(service.load()["players"]) == 1
    assert len(service.load()["characters"]) == 1
    assert len(service.load()["builds"]) == 1


def test_schema_v3_character_gamertag_upgrades_to_player_ownership(tmp_path) -> None:
    path = tmp_path / "characters.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "characters": [
                    {
                        "character_id": "character-1",
                        "name": "Magrat",
                        "gamertag": "Jarakeen",
                        "eso_class": "Warden",
                    }
                ],
                "builds": [],
            }
        ),
        encoding="utf-8",
    )
    service = BuildCatalogService(path)

    catalog = service.load()

    assert catalog["schema_version"] == SCHEMA_VERSION
    assert len(catalog["players"]) == 1
    assert catalog["players"][0]["gamertag"] == "Jarakeen"
    assert catalog["characters"][0]["player_id"] == catalog["players"][0]["player_id"]
