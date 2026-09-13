from services.raid_group_effect_catalog import GROUP_COVERAGE_BY_NAME, GROUP_COVERAGE_NAMES


def test_unique_support_effects_are_visible_in_coverage_catalog():
    expected = {
        "Major Brittle",
        "Off Balance",
        "Powerful Assault",
        "Roar of Alkosh",
        "Touch of Z'en",
        "Way of Martial Knowledge",
        "Spaulder of Ruin",
        "Nazaray",
        "Encratis's Behemoth",
        "Symphony of Blades",
        "Ozezan the Inferno",
    }

    assert expected.issubset(set(GROUP_COVERAGE_NAMES))


def test_unique_support_effects_have_planning_sources_and_are_not_universal_requirements():
    for name in (
        "Major Brittle",
        "Off Balance",
        "Powerful Assault",
        "Roar of Alkosh",
        "Touch of Z'en",
        "Way of Martial Knowledge",
        "Spaulder of Ruin",
        "Nazaray",
        "Encratis's Behemoth",
        "Symphony of Blades",
        "Ozezan the Inferno",
    ):
        row = GROUP_COVERAGE_BY_NAME[name]
        assert row.source_notes
        assert row.default_required is False


def test_unique_support_effect_categories_match_raid_planning_direction():
    assert GROUP_COVERAGE_BY_NAME["Powerful Assault"].category == "Buff"
    assert GROUP_COVERAGE_BY_NAME["Spaulder of Ruin"].category == "Buff"
    assert GROUP_COVERAGE_BY_NAME["Symphony of Blades"].category == "Buff"
    assert GROUP_COVERAGE_BY_NAME["Ozezan the Inferno"].category == "Buff"

    assert GROUP_COVERAGE_BY_NAME["Major Brittle"].category == "Debuff"
    assert GROUP_COVERAGE_BY_NAME["Off Balance"].category == "Debuff"
    assert GROUP_COVERAGE_BY_NAME["Roar of Alkosh"].category == "Debuff"
    assert GROUP_COVERAGE_BY_NAME["Touch of Z'en"].category == "Debuff"
    assert GROUP_COVERAGE_BY_NAME["Way of Martial Knowledge"].category == "Debuff"
    assert GROUP_COVERAGE_BY_NAME["Nazaray"].category == "Debuff"
    assert GROUP_COVERAGE_BY_NAME["Encratis's Behemoth"].category == "Debuff"
