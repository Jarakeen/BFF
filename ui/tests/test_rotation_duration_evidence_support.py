from minmax.rotation_recast import RotationRecastAnalysis, RotationRecastSummary
from services.rotation_duration_analysis_service import RotationDurationProjection
from ui.rotation_duration_evidence_support import RotationDurationEvidenceSupport


def test_duration_evidence_formats_verified_recast_summaries() -> None:
    projection = RotationDurationProjection(
        analysis=RotationRecastAnalysis(
            windows=(),
            summaries=(
                RotationRecastSummary(
                    skill_name="Combat Prayer",
                    bar="front",
                    duration_seconds=10.0,
                    cast_count=6,
                    active_seconds=54.0,
                    uptime_fraction=0.9,
                    total_gap_seconds=2.0,
                    total_premature_seconds=4.0,
                ),
                RotationRecastSummary(
                    skill_name="Expansive Frost Cloak",
                    bar="back",
                    duration_seconds=20.0,
                    cast_count=3,
                    active_seconds=60.0,
                    uptime_fraction=1.0,
                    total_gap_seconds=0.0,
                    total_premature_seconds=1.0,
                ),
            ),
            unresolved=(),
        ),
        rules=(),
        unresolved=("Energy Orb: canonical duration unavailable",),
    )

    evidence = RotationDurationEvidenceSupport.from_projection(projection)

    assert len(evidence.rows) == 2
    assert evidence.rows[0].ability == "Combat Prayer"
    assert evidence.rows[0].bar == "Front"
    assert evidence.rows[0].uptime_percent == 90.0
    assert "Average projected uptime: 95.0%" in evidence.summary
    assert "Total uncovered gap: 2.0s" in evidence.detail
    assert "Premature overlap: 5.0s" in evidence.detail
    assert "Unresolved duration evidence: 1" in evidence.detail


def test_duration_evidence_keeps_no_rule_state_explicit() -> None:
    projection = RotationDurationProjection(
        analysis=RotationRecastAnalysis(windows=(), summaries=(), unresolved=()),
        rules=(),
        unresolved=("Combat Prayer: duration is not positive",),
    )

    evidence = RotationDurationEvidenceSupport.from_projection(projection)

    assert evidence.rows == ()
    assert "none available" in evidence.summary
    assert "remains unresolved" in evidence.detail
    assert evidence.unresolved == ("Combat Prayer: duration is not positive",)
