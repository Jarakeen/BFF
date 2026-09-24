from services.raid_group_effect_catalog import GROUP_COVERAGE_NAMES
from services.raid_unique_support_set_catalog import UNIQUE_SUPPORT_SET_NAMES


def test_current_raid_coverage_catalog_includes_btv_gap_effects() -> None:
    visible = set(GROUP_COVERAGE_NAMES) | set(UNIQUE_SUPPORT_SET_NAMES)

    expected = {
        "Feeding Frenzy",
        "Xoryn's Masterpiece",
        "Major Savagery",
        "Major Prophecy",
        "Martial Knife",
        "Status Knife",
        "Heat Shock (3 stacks)",
        "Aggressive Horn",
        "Minor Evasion",
        "Minor Aegis",
        "Ozezan's Plating",
        "Weakening",
        "Minor Heroism",
    }
    assert expected <= visible
    assert len(visible) >= 77
