import json
from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from services.canonical_build_bridge import CanonicalBuildBridge


def test_bridge_recovers_populated_legacy_when_catalog_has_only_placeholder_builds(
    tmp_path: Path,
):
    legacy_path = tmp_path / "builds.json"
    catalog_path = tmp_path / "characters.json"
    bridge = CanonicalBuildBridge(legacy_path, catalog_path)

    real = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        EsoClass="Warden",
        Race="Breton",
        Role="Healer",
        AttributeMagicka=64,
        Mundus="The Ritual",
        Food="Witchmother's Potent Brew",
    )
    legacy_path.write_text(
        json.dumps(BuildRoster(Members=[real]).to_dict(), indent=2),
        encoding="utf-8",
    )

    placeholder = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        EsoClass="Warden",
        Race="Breton",
        Role="Healer",
    ).to_dict()
    for field in (
        "AttributeHealth",
        "AttributeMagicka",
        "AttributeStamina",
        "Mundus",
        "Food",
        "Potion",
    ):
        placeholder[field] = 0 if field.startswith("Attribute") else ""

    # Remove the identity fields from the meaningful-data test so this mirrors
    # the historical catalog state seen by the Phase 5 real-build audit.
    for field in (
        "Name",
        "Gamertag",
        "BuildName",
        "Race",
        "EsoClass",
        "Role",
        "CharacterId",
        "BuildId",
    ):
        placeholder[field] = ""

    bridge.catalog_service.save(
        {
            "schema_version": 2,
            "characters": [],
            "builds": [
                {
                    "build_id": "placeholder",
                    "character_id": "magrat",
                    "name": "DF Healer",
                    "legacy": placeholder,
                }
            ],
        }
    )

    loaded = bridge.load()

    assert len(loaded.Members) == 1
    recovered = loaded.Members[0]
    assert recovered.BuildName == "DF Healer"
    assert recovered.AttributeMagicka == 64
    assert recovered.Mundus == "The Ritual"
    assert recovered.Food == "Witchmother's Potent Brew"

    canonical = bridge.catalog_service.load()
    assert len(canonical["builds"]) == 1
    assert canonical["builds"][0]["legacy"]["AttributeMagicka"] == 64
    assert canonical["builds"][0]["legacy"]["Mundus"] == "The Ritual"
