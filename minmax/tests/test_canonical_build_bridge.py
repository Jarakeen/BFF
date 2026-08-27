from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from services.canonical_build_bridge import CanonicalBuildBridge


def test_bridge_loads_canonical_builds_when_catalog_exists(tmp_path: Path):
    legacy = tmp_path / "builds.json"
    catalog = tmp_path / "characters.json"
    bridge = CanonicalBuildBridge(legacy, catalog)

    roster = BuildRoster(
        Members=[
            PlayerBuild(Name="Magrat", Gamertag="Jarakeen", BuildName="DF Healer", EsoClass="Warden")
        ]
    )
    bridge.save(roster)

    legacy.write_text('{"Members": []}', encoding="utf-8")

    loaded = bridge.load()
    assert len(loaded.Members) == 1
    assert loaded.Members[0].BuildName == "DF Healer"
    assert loaded.Members[0].Gamertag == "Jarakeen"


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
