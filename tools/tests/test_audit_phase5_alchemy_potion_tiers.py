from __future__ import annotations

import json
from pathlib import Path

from tools.audit_phase5_alchemy_potion_tiers import load_effects, potion_tier_rows


def test_load_effects_indexes_effect_names_case_insensitively(tmp_path: Path):
    path = tmp_path / "alchemy_effects.json"
    path.write_text(
        json.dumps(
            {
                "effects": [
                    {
                        "effect_name": "Restore Magicka",
                        "potion_tiers": [
                            {
                                "solvent": "Lorkhan's Tears",
                                "level": "CP 150",
                                "name": "Essence of Magicka",
                                "values": ["7582 Magicka"],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    effects = load_effects(path)

    assert "restore magicka" in effects
    assert effects["restore magicka"]["effect_name"] == "Restore Magicka"


def test_potion_tier_rows_rejects_non_dict_entries():
    effect = {
        "potion_tiers": [
            {"solvent": "A", "values": ["1"]},
            "bad row",
            None,
        ]
    }

    assert potion_tier_rows(effect) == ({"solvent": "A", "values": ["1"]},)
