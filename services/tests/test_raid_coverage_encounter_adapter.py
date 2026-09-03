import pytest

from services.encounter_requirement_evaluation import RequirementSemantics
from services.encounter_requirement_overlay import EncounterRequirementOverlayService
from services.encounter_service import EncounterRequirement
from services.raid_coverage_encounter_adapter import RaidCoverageEncounterAdapter
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE


class _BaseEncounterService:
    def requirements(self, encounter_id: str):
        return (
            EncounterRequirement(
                requirement_id=f"{encounter_id}:mechanic:1:requirement:movement",
                encounter_id=encounter_id,
                mechanic_id=f"{encounter_id}:mechanic:1",
                mechanic_name="Move",
                requirement_type="movement",
                target_count=None,
                interpretation_status="source",
            ),
        )


def test_coverage_adapter_emits_only_exact_mapped_provider_requirement():
    adapter = RaidCoverageEncounterAdapter(DEFAULT_RAID_COVERAGE_PROFILE)

    rows = adapter.requirements("oaxiltso")

    assert len(rows) == 1
    assert rows[0].requirement_id == "oaxiltso:coverage:war_horn"
    assert rows[0].encounter_id == "oaxiltso"
    assert rows[0].mechanic_id == "coverage-profile:default_raid_coverage"
    assert rows[0].mechanic_name == "War Horn"
    assert rows[0].requirement_type == "force"
    assert rows[0].interpretation_status == "configured_raid_coverage"


def test_coverage_adapter_marks_mapped_capability_as_provider_semantics():
    adapter = RaidCoverageEncounterAdapter(DEFAULT_RAID_COVERAGE_PROFILE)

    assert adapter.requirement_semantics() == {
        "force": RequirementSemantics.PROVIDER_CAPABILITY
    }
    assert adapter.required_provider_counts("oaxiltso") == {
        "oaxiltso:coverage:war_horn": 1
    }


def test_coverage_adapter_exposes_exact_effect_identity_map():
    adapter = RaidCoverageEncounterAdapter(DEFAULT_RAID_COVERAGE_PROFILE)

    maps = adapter.capability_identity_maps()

    assert len(maps) == 1
    assert maps[0].capability_type == "force"
    assert maps[0].effect_names == frozenset({"force"})


def test_requirement_overlay_preserves_canonical_rows_and_appends_profile_rows():
    adapter = RaidCoverageEncounterAdapter(DEFAULT_RAID_COVERAGE_PROFILE)
    overlay = EncounterRequirementOverlayService(
        _BaseEncounterService(),
        {"oaxiltso": adapter.requirements("oaxiltso")},
    )

    rows = overlay.requirements("oaxiltso")

    assert [row.requirement_type for row in rows] == ["movement", "force"]


def test_requirement_overlay_rejects_wrong_encounter_identity():
    adapter = RaidCoverageEncounterAdapter(DEFAULT_RAID_COVERAGE_PROFILE)

    with pytest.raises(ValueError, match="must match"):
        EncounterRequirementOverlayService(
            _BaseEncounterService(),
            {"other": adapter.requirements("oaxiltso")},
        )


def test_requirement_overlay_rejects_collision_with_canonical_requirement_id():
    collision = EncounterRequirement(
        requirement_id="oaxiltso:mechanic:1:requirement:movement",
        encounter_id="oaxiltso",
        mechanic_id="coverage-profile:test",
        mechanic_name="Collision",
        requirement_type="force",
        target_count=None,
        interpretation_status="configured_raid_coverage",
    )
    overlay = EncounterRequirementOverlayService(
        _BaseEncounterService(),
        {"oaxiltso": (collision,)},
    )

    with pytest.raises(ValueError, match="collide"):
        overlay.requirements("oaxiltso")
