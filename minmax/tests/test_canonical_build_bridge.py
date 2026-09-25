from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from services.canonical_build_bridge import CanonicalBuildBridge


def test_bridge_loads_canonical_builds_when_catalog_exists(tmp_path: Path):
    legacy = tmp_path / "builds.json"
    catalog = tmp_path / "characters.json"
    bridge = CanonicalBuildBridge(legacy, catalog)

    roster = BuildRoster(
        Members=[
            PlayerBuild(
                Name="Magrat",
                Gamertag="Jarakeen",
                BuildName="DF Healer",
                EsoClass="Warden",
                AttributeMagicka=64,
                Mundus="The Ritual",
            )
        ]
    )
    bridge.save(roster)

    legacy.write_text('{"Members": []}', encoding="utf-8")

    loaded = bridge.load()
    assert len(loaded.Members) == 1
    assert loaded.Members[0].BuildName == "DF Healer"
    assert loaded.Members[0].Gamertag == "Jarakeen"
    assert loaded.Members[0].AttributeMagicka == 64
    assert loaded.Members[0].Mundus == "The Ritual"


def test_bridge_save_keeps_legacy_mirror_and_canonical_catalog(tmp_path: Path):
    bridge = CanonicalBuildBridge(tmp_path / "builds.json", tmp_path / "characters.json")
    roster = BuildRoster(
        Members=[
            PlayerBuild(Name="Magrat", Gamertag="Jarakeen", BuildName="Parse", EsoClass="Warden"),
            PlayerBuild(Name="Magrat", Gamertag="Jarakeen", BuildName="DSR HM", EsoClass="Warden"),
        ]
    )

    bridge.save(roster)

    catalog = bridge.catalog_service.load()
    assert len(catalog["characters"]) == 1
    assert len(catalog["builds"]) == 2
    assert {build["name"] for build in catalog["builds"]} == {"Parse", "DSR HM"}


def test_bridge_keeps_incomplete_canonical_saved_build_visible(tmp_path: Path):
    """A canonical Saved Build must not vanish behind legacy completeness rules."""
    legacy = tmp_path / "builds.json"
    catalog = tmp_path / "characters.json"
    bridge = CanonicalBuildBridge(legacy, catalog)

    bridge.catalog_service.save(
        {
            "schema_version": 2,
            "players": [
                {
                    "player_id": "player-rik",
                    "gamertag": "Rikbacon",
                    "status": "Active",
                }
            ],
            "characters": [
                {
                    "character_id": "character-bacon",
                    "player_id": "player-rik",
                    "name": "Bacon",
                    "gamertag": "Rikbacon",
                    "eso_class": "Sorcerer",
                    "race": "",
                    "role": "Tank",
                    "alliance": "",
                    "vampire": False,
                    "werewolf": False,
                    "owned_skill_lines": [],
                }
            ],
            "builds": [
                {
                    "build_id": "build-rik-tank",
                    "character_id": "character-bacon",
                    "name": "Rik — Sorcerer Tank",
                    "payload": {
                        "Name": "Bacon",
                        "Gamertag": "Rikbacon",
                        "BuildName": "Rik — Sorcerer Tank",
                        "EsoClass": "Sorcerer",
                        "Role": "Tank",
                    },
                }
            ],
            "team_assignments": [],
        }
    )

    loaded = bridge.load()

    assert len(loaded.Members) == 1
    build = loaded.Members[0]
    assert build.BuildId == "build-rik-tank"
    assert build.CharacterId == "character-bacon"
    assert build.Gamertag == "Rikbacon"
    assert build.Name == "Bacon"
    assert build.BuildName == "Rik — Sorcerer Tank"
    assert build.BuildKind == "saved"
