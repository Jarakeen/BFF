import pytest

from services.raid_coverage_profile import (
    DEFAULT_RAID_COVERAGE_PROFILE,
    RaidCoverageProfile,
    RaidCoverageRequirement,
)


def test_default_profile_preserves_existing_required_watch_list():
    assert tuple(row.display_name for row in DEFAULT_RAID_COVERAGE_PROFILE.requirements) == (
        "Major Courage",
        "Major Vulnerability",
        "Major Berserk",
        "Major Breach",
        "Major Slayer",
        "Crusher",
        "Minor Brittle",
        "Minor Maim",
        "War Horn",
        "Orbs",
        "Purify",
        "Magickasteal",
        "Minor Resolve",
        "Minor Intellect",
        "Minor Force",
    )
    assert all(row.required for row in DEFAULT_RAID_COVERAGE_PROFILE.requirements)


def test_default_profile_maps_only_source_backed_capability_identities():
    assert [(row.display_name, row.capability_type) for row in DEFAULT_RAID_COVERAGE_PROFILE.mapped_required] == [
        ("Major Courage", "major_courage"),
        ("Major Slayer", "major_slayer"),
        ("Minor Brittle", "minor_brittle"),
        ("Minor Maim", "minor_maim"),
        ("War Horn", "force"),
    ]
    assert len(DEFAULT_RAID_COVERAGE_PROFILE.unmapped_required) == 10


def test_profile_emits_only_mapped_required_coverage_requirements():
    requirements = DEFAULT_RAID_COVERAGE_PROFILE.coverage_requirements()

    assert [row.effect_name for row in requirements] == [
        "major_courage",
        "major_slayer",
        "minor_brittle",
        "minor_maim",
        "force",
    ]
    assert all(row.required_provider_count == 1 for row in requirements)


def test_unmapped_display_name_is_not_guessed_into_capability_type():
    row = RaidCoverageRequirement("major_vulnerability", "Major Vulnerability")

    assert row.capability_type is None
    assert row.to_coverage_requirement() is None


def test_mapped_requirement_requires_provenance():
    with pytest.raises(ValueError, match="require mapping_evidence"):
        RaidCoverageRequirement(
            "war_horn",
            "War Horn",
            capability_type="force",
        )


def test_profile_rejects_duplicate_requirement_ids():
    row = RaidCoverageRequirement("same", "One")

    with pytest.raises(ValueError, match="duplicate requirement_id"):
        RaidCoverageProfile("profile", "Profile", (row, row))
