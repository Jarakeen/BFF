import json
from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from services.canonical_build_bridge import CanonicalBuildBridge


def test_bridge_recovers_populated_legacy_when_catalog_has_identity_only_build(
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

    # This mirrors the Phase 5 audit failure: the canonical record knows who
    # the character/build is, but the embedded legacy snapshot contains no
    # actual build selections. Identity metadata must not make it authoritative.
    placeholder = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        EsoClass="Warden",
        Race="Breton",
        Role="Healer",
    ).to_dict()

    bridge.catalog_service.save(
        {
            "schema_version": 2,
            "characters": [
                {
                    "character_id": "magrat",
                    "name": "Magrat",
                    "gamertag": "Jarakeen",
                    "eso_class": "Warden",
                    "race": "Breton",
                    "role": "Healer",
                    "alliance": "",
                    "vampire": False,
                    "werewolf": False,
                    "owned_skill_lines": [],
                }
            ],
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
    assert canonical["builds"][0]["legacy"]["Name"] == "Magrat"
    assert canonical["builds"][0]["legacy"]["BuildName"] == "DF Healer"
    assert canonical["builds"][0]["legacy"]["AttributeMagicka"] == 64
    assert canonical["builds"][0]["legacy"]["Mundus"] == "The Ritual"
