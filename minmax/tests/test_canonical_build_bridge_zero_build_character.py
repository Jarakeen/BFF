from __future__ import annotations

from models.build_model import BuildRoster, PlayerBuild
from services.canonical_build_bridge import CanonicalBuildBridge


def test_character_and_progression_survive_removing_last_build(tmp_path):
    legacy_path = tmp_path / "builds.json"
    catalog_path = tmp_path / "characters.json"
    bridge = CanonicalBuildBridge(legacy_path, catalog_path)

    build = PlayerBuild(Name="Magrat", Gamertag="Jarakeen", BuildName="DF Healer")
    build.Food = "Witchmother's Potent Brew"
    bridge.save(BuildRoster(Members=[build]))

    catalog = bridge.catalog_service.load()
    character_id = catalog["characters"][0]["character_id"]
    bridge.catalog_service.set_passive_rank(
        character_id=character_id,
        passive_name="Flourish",
        rank=2,
    )

    bridge.save(BuildRoster())

    saved = bridge.catalog_service.load()
    assert saved["builds"] == []
    assert len(saved["characters"]) == 1
    assert saved["characters"][0]["character_id"] == character_id
    assert saved["characters"][0]["passive_ranks"]["Flourish"] == 2
