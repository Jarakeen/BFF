import json

from models.build_model import BuildRoster, GearSlot, PlayerBuild
from services.canonical_build_bridge import CanonicalBuildBridge


def _invalid_roster() -> BuildRoster:
    return BuildRoster(
        Members=[
            PlayerBuild(
                Name="Rylonia",
                BuildName="Corpsebuster DD",
                Role="DD",
                Ring2=GearSlot(
                    Set="Test Set",
                    Trait="Bloodthirsty",
                    Enchant="Weapon Damage",
                    EnchantTier="Truly Superb",
                    Level="CP70",
                ),
            )
        ]
    )


def test_save_normalizes_impossible_truly_superb_level_before_persistence(tmp_path) -> None:
    builds_path = tmp_path / "builds.json"
    bridge = CanonicalBuildBridge(builds_path)

    bridge.save(_invalid_roster())

    payload = json.loads(builds_path.read_text(encoding="utf-8"))
    assert payload["Members"][0]["Ring2"]["EnchantTier"] == "Truly Superb"
    assert payload["Members"][0]["Ring2"]["Level"] == "CP160"


def test_load_repairs_legacy_impossible_pair_in_memory(tmp_path) -> None:
    builds_path = tmp_path / "builds.json"
    builds_path.write_text(
        json.dumps(_invalid_roster().to_dict()),
        encoding="utf-8",
    )
    bridge = CanonicalBuildBridge(builds_path)

    roster = bridge.load()

    assert roster.Members[0].Name == "Rylonia"
    assert roster.Members[0].Ring2.EnchantTier == "Truly Superb"
    assert roster.Members[0].Ring2.Level == "CP160"
