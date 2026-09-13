from pathlib import Path

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_duration_analysis_service import RotationDurationAnalysisService


ROOT = Path(__file__).resolve().parents[2]


def test_venom_skull_reviewed_direct_damage_does_not_require_duration_rule() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Venom Skull",
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Venom Skull",
                bar="front",
            ),
        ),
    )

    projection = RotationDurationAnalysisService(
        database_path=ROOT / "data" / "eso.db",
    ).analyze(plan)

    assert projection.rules == ()
    assert not any("Venom Skull" in message for message in projection.unresolved)


def test_missing_duration_still_fails_closed_without_reviewed_direct_identity() -> None:
    plan = RotationPlan(
        character_name="test",
        build_name="unknown",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Definitely Not A Reviewed Skill",
                bar="front",
            ),
        ),
    )

    projection = RotationDurationAnalysisService(
        database_path=ROOT / "data" / "eso.db",
    ).analyze(plan)

    assert projection.rules == ()
    assert projection.unresolved
