from __future__ import annotations

import json

from tools.audit_weapon_enchantment_raw_metadata import audit_source


def test_audit_source_inventories_fields_and_interesting_values(tmp_path):
    source = tmp_path / "weapon_enchantments.json"
    source.write_text(
        json.dumps(
            {
                "minedItemSummary": [
                    {
                        "itemId": 1,
                        "name": "Glyph of Flame",
                        "defaultEnchantId": 77,
                        "cooldownMs": 4000,
                        "ordinary": "ignored-from-interesting-values",
                    },
                    {
                        "itemId": 2,
                        "name": "Glyph of Frost",
                        "defaultEnchantId": 78,
                        "cooldownMs": 4000,
                        "abilityId": 9001,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    key_counts, interesting = audit_source(source)

    assert key_counts["itemId"] == 2
    assert key_counts["cooldownMs"] == 2
    assert interesting["cooldownMs"]["4000"] == 2
    assert interesting["defaultEnchantId"]["77"] == 1
    assert interesting["defaultEnchantId"]["78"] == 1
    assert interesting["abilityId"]["9001"] == 1
    assert "ordinary" not in interesting
