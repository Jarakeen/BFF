from pathlib import Path

from models.build_model import PlayerBuild
from services.canonical_build_bridge import CanonicalBuildBridge


def test_bridge_ignores_empty_legacy_builds_in_canonical_catalog(tmp_path: Path):
    bridge = CanonicalBuildBridge(tmp_path / "builds.json", tmp_path / "characters.json")
    real = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        EsoClass="Warden",
        Race="Breton",
        Role="Healer",
        AttributeMagicka=64,
        Mundus="The Ritual",
    )
    blank = PlayerBuild()

    bridge.catalog_service.save({
        "schema_version": 2,
        "characters": [],
        "builds": [
            {"build_id": "real", "character_id": "magrat", "name": "DF Healer", "legacy": real.to_dict()},
            {"build_id": "blank", "character_id": "ghost", "name": "", "legacy": blank.to_dict()},
        ],
    })

    loaded = bridge.load()

    assert len(loaded.Members) == 1
    assert loaded.Members[0].BuildName == "DF Healer"
    assert loaded.Members[0].Gamertag == "Jarakeen"
    assert loaded.Members[0].AttributeMagicka == 64
    assert loaded.Members[0].Mundus == "The Ritual"
