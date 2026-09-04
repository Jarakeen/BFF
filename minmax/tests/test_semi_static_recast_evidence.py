from minmax.rotation_duration_evidence import (
    RotationDurationEvidence,
    RotationDurationResolution,
)
from minmax.rotation_plan import RotationActionKind
from minmax.semi_static_recast_evidence import (
    assess_semi_static_recast_evidence,
    assess_semi_static_rotation_recasts,
)
from minmax.semi_static_rotation import SemiStaticRotationEntry


def _resolution(skill_name: str) -> RotationDurationResolution:
    return RotationDurationResolution(
        skill_name=skill_name,
        ability_id=12345,
        evidence=(
            RotationDurationEvidence(
                effect_name="minor_berserk",
                duration_seconds=8.0,
                source=skill_name,
            ),
            RotationDurationEvidence(
                effect_name="minor_resolve",
                duration_seconds=10.0,
                source=skill_name,
            ),
        ),
    )


def test_recast_evidence_reports_exact_match_without_promoting_policy(monkeypatch) -> None:
    monkeypatch.setattr(
        "minmax.semi_static_recast_evidence.resolve_rotation_duration_evidence",
        lambda skill_name, database_path=None: _resolution(skill_name),
    )
    entry = SemiStaticRotationEntry(
        first_time_seconds=0.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Combat Prayer",
        bar="front",
        recast_interval_seconds=8.0,
    )

    assessment = assess_semi_static_recast_evidence(entry)

    assert assessment is not None
    assert assessment.skill_name == "Combat Prayer"
    assert assessment.recast_interval_seconds == 8.0
    assert assessment.canonical_durations_seconds == (8.0, 10.0)
    assert assessment.matches_canonical_duration is True
    assert [item.effect_name for item in assessment.matching_evidence] == [
        "minor_berserk"
    ]
    assert assessment.duration_resolution.evidence[1].duration_seconds == 10.0


def test_recast_evidence_preserves_manual_interval_when_no_duration_matches(monkeypatch) -> None:
    monkeypatch.setattr(
        "minmax.semi_static_recast_evidence.resolve_rotation_duration_evidence",
        lambda skill_name, database_path=None: _resolution(skill_name),
    )
    entry = SemiStaticRotationEntry(
        first_time_seconds=0.0,
        sequence=0,
        kind=RotationActionKind.SKILL,
        name="Combat Prayer",
        recast_interval_seconds=7.0,
    )

    assessment = assess_semi_static_recast_evidence(entry)

    assert assessment is not None
    assert assessment.recast_interval_seconds == 7.0
    assert assessment.canonical_durations_seconds == (8.0, 10.0)
    assert assessment.matches_canonical_duration is False
    assert assessment.matching_evidence == ()


def test_bulk_recast_assessment_ignores_one_shots_and_non_skill_repeats(monkeypatch) -> None:
    monkeypatch.setattr(
        "minmax.semi_static_recast_evidence.resolve_rotation_duration_evidence",
        lambda skill_name, database_path=None: _resolution(skill_name),
    )
    entries = (
        SemiStaticRotationEntry(
            first_time_seconds=0.0,
            sequence=0,
            kind=RotationActionKind.SKILL,
            name="Combat Prayer",
            recast_interval_seconds=8.0,
        ),
        SemiStaticRotationEntry(
            first_time_seconds=1.0,
            sequence=1,
            kind=RotationActionKind.SKILL,
            name="Overflowing Altar",
        ),
        SemiStaticRotationEntry(
            first_time_seconds=2.0,
            sequence=2,
            kind=RotationActionKind.LIGHT_ATTACK,
            recast_interval_seconds=1.0,
        ),
    )

    assessments = assess_semi_static_rotation_recasts(entries)

    assert len(assessments) == 1
    assert assessments[0].skill_name == "Combat Prayer"
