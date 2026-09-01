from __future__ import annotations

import json
from pathlib import Path

from minmax.alchemy_potion_tier_repository import AlchemyPotionTierRepository


def _write_payload(path: Path) -> None:
    payload = {
        "effects": [
            {
                "effect_name": "Restore Magicka",
                "potion_tiers": [
                    {
                        "solvent": "Potion [ edit ] concatenated header",
                        "level": "Solvent",
                        "name": "Level",
                        "values": ["Potion", "Magicka Restored", "Duration", "Triple Duration"],
                    },
                    {
                        "solvent": "Star Dew",
                        "level": "100",
                        "name": "Distillate of Magicka",
                        "values": ["7103", "34.0", "38.0"],
                    },
                    {
                        "solvent": "Lorkhan's Tears",
                        "level": "150",
                        "name": "Essence of Magicka",
                        "values": ["7582", "36.6", "40.6"],
                    },
                    {
                        "solvent": "Alkahest",
                        "level": "150",
                        "name": "Drain Magicka Poison IX",
                        "values": ["238", "5.8", "6.0"],
                    },
                ],
            },
            {
                "effect_name": "Increase Spell Power",
                "potion_tiers": [
                    {
                        "solvent": "Lorkhan's Tears",
                        "level": "150",
                        "name": "Essence of Spell Power",
                        "values": ["36.6", "40.6"],
                    }
                ],
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_filters_malformed_header_and_poison_rows(tmp_path: Path):
    source = tmp_path / "alchemy_effects.json"
    _write_payload(source)

    tiers = AlchemyPotionTierRepository(source).tiers("Restore Magicka")

    assert [tier.potion_name for tier in tiers] == ["Distillate of Magicka", "Essence of Magicka"]


def test_restore_trait_exposes_magnitude_and_both_duration_columns(tmp_path: Path):
    source = tmp_path / "alchemy_effects.json"
    _write_payload(source)

    tier = AlchemyPotionTierRepository(source).max_tier("Restore Magicka")

    assert tier is not None
    assert tier.solvent == "Lorkhan's Tears"
    assert tier.level == 150
    assert tier.magnitude == 7582.0
    assert tier.duration == 36.6
    assert tier.triple_duration == 40.6


def test_timed_trait_has_no_invented_magnitude(tmp_path: Path):
    source = tmp_path / "alchemy_effects.json"
    _write_payload(source)

    tier = AlchemyPotionTierRepository(source).max_tier("Increase Spell Power")

    assert tier is not None
    assert tier.magnitude is None
    assert tier.duration == 36.6
    assert tier.triple_duration == 40.6
