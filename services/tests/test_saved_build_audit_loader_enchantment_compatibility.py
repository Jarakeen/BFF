import json

from tools.audit_phase13_saved_build_rotation_timing import _load_build


def test_saved_build_audit_loader_normalizes_truly_superb_level(tmp_path) -> None:
    builds = tmp_path / "builds.json"
    builds.write_text(
        json.dumps(
            {
                "Members": [
                    {
                        "Name": "Rylonia",
                        "BuildName": "Corpsebuster DD",
                        "Role": "DD",
                        "Ring2": {
                            "Set": "Test Set",
                            "Trait": "Bloodthirsty",
                            "Enchant": "Weapon Damage",
                            "Quality": "Gold",
                            "EnchantTier": "Truly Superb",
                            "Level": "CP70",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    build = _load_build(builds, "Corpsebuster DD", "Rylonia")

    assert build.Ring2.EnchantTier == "Truly Superb"
    assert build.Ring2.Level == "CP160"
