from __future__ import annotations

from models.raid_plan import RaidPlanMember
from services.raid_readiness_evidence_service import (
    COVERAGE_EFFECT_NAMES,
    RaidReadinessEvidenceService,
)


def test_planned_comp_state_counts_as_planned_build_evidence() -> None:
    member = RaidPlanMember(
        seat_id="DD1",
        gamertag="Rylo",
        planned_gear_sets=("Corpseburster", "Null Arca"),
    )
    assert RaidReadinessEvidenceService._planned_build(member) is True


def test_empty_chair_has_no_planned_build_evidence() -> None:
    member = RaidPlanMember(seat_id="DD1", gamertag="Rylo")
    assert RaidReadinessEvidenceService._planned_build(member) is False


def test_only_named_coverage_assignments_are_classified_as_coverage_duties() -> None:
    known = COVERAGE_EFFECT_NAMES[0]
    member = RaidPlanMember(
        seat_id="Tank1",
        gamertag="Rikbacon",
        primary_assignment=known,
        secondary_assignment="Portal",
    )
    assert RaidReadinessEvidenceService._assigned_coverage_effects(member) == (known,)


def test_noncoverage_jobs_do_not_become_fake_coverage_gaps() -> None:
    member = RaidPlanMember(
        seat_id="DD1",
        gamertag="Rylo",
        primary_assignment="Portal",
        secondary_assignment="Kite",
    )
    assert RaidReadinessEvidenceService._assigned_coverage_effects(member) == ()
