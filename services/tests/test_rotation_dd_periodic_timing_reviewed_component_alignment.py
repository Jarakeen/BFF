from pathlib import Path

from minmax.rotation_plan import RotationAction, RotationActionKind
from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationCandidatePeriodicDamageTimingEvidenceService,
)


ROOT = Path(__file__).resolve().parents[2]


def test_default_periodic_timing_sees_reviewed_stampede_dot_component() -> None:
    service = RotationCandidatePeriodicDamageTimingEvidenceService(
        ROOT / "data" / "eso.db"
    )
    action = RotationAction(
        time_seconds=10.0,
        sequence=1,
        kind=RotationActionKind.SKILL,
        name="Stampede",
        bar="back",
    )

    report = service.inspect_action(action)

    coefficient_two = tuple(
        entry for entry in report.entries if entry.coefficient_number == 2
    )
    assert len(coefficient_two) == 1
    entry = coefficient_two[0]
    assert entry.source_name == "Stampede"
    assert entry.duration_seconds == 15.0
    assert entry.timing is not None
    assert entry.timing.interval_seconds == 1.0


def test_default_periodic_timing_keeps_boneyard_reviewed_periodic_identity_visible() -> None:
    service = RotationCandidatePeriodicDamageTimingEvidenceService(
        ROOT / "data" / "eso.db"
    )
    action = RotationAction(
        time_seconds=1.0,
        sequence=1,
        kind=RotationActionKind.SKILL,
        name="Unnerving Boneyard",
        bar="front",
    )

    report = service.inspect_action(action)

    assert any(entry.coefficient_number == 1 for entry in report.entries)
