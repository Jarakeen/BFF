from __future__ import annotations

from dataclasses import replace

from minmax.fight_damage_trajectory import RaidDamageSegment
from services.encounter_boss_guide import (
    BossGuideTimelineFact,
    EncounterBossGuide,
)
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjectionService,
)


def _guide(*, health: str = "100,000,000") -> EncounterBossGuide:
    return EncounterBossGuide(
        encounter_id="xalvakka",
        content_id="rockgrove",
        content_name="Rockgrove",
        name="Xalvakka",
        summary="",
        location="",
        species="",
        reaction="",
        health_record_present=True,
        health=(("hardmode", health),),
        abilities=(),
        phases=(),
        structural_phases=(),
        timeline_facts=(
            BossGuideTimelineFact(
                fact_id=1,
                canonical_kind="phase",
                fact_type="phase",
                fact_key="phase_2",
                payload={"threshold": "70%", "label": "Phase 2"},
                review_status="reviewed_corroborated",
                evidence_count=3,
            ),
            BossGuideTimelineFact(
                fact_id=2,
                canonical_kind="phase_transition",
                fact_type="transition",
                fact_key="retreat_thresholds",
                payload={"thresholds": ["70%", "40%"], "event": "retreat"},
                review_status="reviewed_corroborated",
                evidence_count=3,
            ),
        ),
        source_url="",
        source_page_title="",
        source_revision_id="",
        retrieved_at="",
        source_license="",
    )


def test_projects_reviewed_health_thresholds_to_clock_points() -> None:
    result = EncounterHealthThresholdProjectionService().project(
        guide=_guide(),
        difficulty="hardmode",
        damage_segments=(RaidDamageSegment(0.0, None, 1_000_000.0, "test raid DPS"),),
    )

    assert result.maximum_health == 100_000_000
    assert [(row.fact_key, row.threshold_fraction, row.time_seconds) for row in result.points] == [
        ("phase_2", 0.70, 30.0),
        ("retreat_thresholds", 0.70, 30.0),
        ("retreat_thresholds", 0.40, 60.0),
    ]
    assert result.unresolved == ()


def test_missing_or_ambiguous_health_blocks_projection() -> None:
    result = EncounterHealthThresholdProjectionService().project(
        guide=_guide(health="about 100 million"),
        difficulty="hardmode",
        damage_segments=(RaidDamageSegment(0.0, None, 1_000_000.0),),
    )

    assert result.maximum_health is None
    assert result.trajectory is None
    assert result.points == ()
    assert "not unambiguously numeric" in result.unresolved[0]


def test_finite_damage_trajectory_preserves_unresolved_late_threshold() -> None:
    result = EncounterHealthThresholdProjectionService().project(
        guide=_guide(),
        difficulty="hardmode",
        damage_segments=(RaidDamageSegment(0.0, 35.0, 1_000_000.0),),
    )

    phase_2 = next(row for row in result.points if row.fact_key == "phase_2")
    late_retreat = next(
        row
        for row in result.points
        if row.fact_key == "retreat_thresholds" and row.threshold_fraction == 0.40
    )
    assert phase_2.resolved is True
    assert late_retreat.resolved is False
    assert late_retreat.time_seconds is None
    assert any("40%" in message and "ends before" in message for message in result.unresolved)


def test_unreviewed_or_evidence_free_threshold_facts_are_not_projected() -> None:
    guide = _guide()
    first, second = guide.timeline_facts
    guide = replace(
        guide,
        timeline_facts=(
            replace(first, review_status="review_required"),
            replace(second, evidence_count=0),
        ),
    )

    result = EncounterHealthThresholdProjectionService().project(
        guide=guide,
        difficulty="hardmode",
        damage_segments=(RaidDamageSegment(0.0, None, 1_000_000.0),),
    )

    assert result.points == ()
    assert result.trajectory is None
    assert result.unresolved == ("no reviewed canonical health-threshold facts are available",)
