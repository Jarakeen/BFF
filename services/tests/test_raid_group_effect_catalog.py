from services.raid_group_effect_catalog import (
    GROUP_COVERAGE_BY_NAME,
    GROUP_COVERAGE_NAMES,
    GROUP_DEBUFF_NAMES,
)


def test_group_coverage_catalog_contains_requested_group_effects():
    expected = {
        "Major Courage",
        "Minor Courage",
        "Major Force",
        "Minor Force",
        "Major Slayer",
        "Minor Berserk",
        "Major Brutality",
        "Major Sorcery",
        "Minor Brutality",
        "Minor Sorcery",
        "Minor Savagery",
        "Minor Prophecy",
        "Major Resolve",
        "Minor Resolve",
        "Major Protection",
        "Minor Protection",
        "Major Evasion",
        "Major Heroism",
        "Major Vitality",
        "Minor Vitality",
        "Major Fortitude",
        "Minor Fortitude",
        "Major Intellect",
        "Minor Intellect",
        "Major Endurance",
        "Minor Endurance",
        "Major Expedition",
        "Minor Expedition",
        "Empower",
        "Major Vulnerability",
        "Minor Vulnerability",
        "Major Breach",
        "Minor Breach",
        "Major Maim",
        "Minor Maim",
        "Major Cowardice",
        "Minor Cowardice",
        "Major Defile",
        "Minor Defile",
        "Minor Brittle",
        "Minor Lifesteal",
        "Magickasteal",
        "Minor Timidity",
        "Minor Enervation",
        "Minor Uncertainty",
        "Crusher",
    }
    assert expected <= set(GROUP_COVERAGE_NAMES)


def test_group_coverage_catalog_excludes_assignment_and_ad_hoc_utility_jobs():
    excluded = {"Kite", "Portal", "Interrupts", "Orbs", "Purify", "War Horn"}
    assert excluded.isdisjoint(GROUP_COVERAGE_NAMES)


def test_magickasteal_remains_a_debuff_not_utility():
    assert "Magickasteal" in GROUP_DEBUFF_NAMES
    assert GROUP_COVERAGE_BY_NAME["Magickasteal"].category == "Debuff"


def test_every_group_effect_has_source_guidance():
    assert GROUP_COVERAGE_BY_NAME
    for reference in GROUP_COVERAGE_BY_NAME.values():
        assert reference.source_notes
        assert all(note.strip() for note in reference.source_notes)
