from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.rotation_dd_parse_objective_service import (
    DEFAULT_TRIAL_DUMMY_HEALTH,
    RotationDDParseCandidateEvidence,
    RotationDDParseObjective,
    RotationDDParseObjectiveService,
    RotationDDParseProjectionState,
)


def _scorecard(*, eligible: bool = True):
    return SimpleNamespace(supplied_obligations_satisfied=eligible)


def test_default_parse_objective_uses_21m_target() -> None:
    objective = RotationDDParseObjective()

    assert objective.target_health == 21_000_000.0
    assert objective.target_health == DEFAULT_TRIAL_DUMMY_HEALTH


def test_parse_objective_is_caller_overridable() -> None:
    objective = RotationDDParseObjective(target_health=10_000_000)

    assert objective.target_health == 10_000_000.0


def test_120k_projection_requests_175_second_horizon() -> None:
    service = RotationDDParseObjectiveService()
    evidence = RotationDDParseCandidateEvidence(
        candidate_id="candidate-a",
        scorecard=_scorecard(),
        projected_duration_seconds=60.0,
        projected_total_damage=7_200_000.0,
    )

    assessment = service.assess(
        objective=RotationDDParseObjective(),
        evidence=evidence,
    )

    assert assessment.state is RotationDDParseProjectionState.NEEDS_LONGER_PROJECTION
    assert assessment.projected_dps == pytest.approx(120_000.0)
    assert assessment.estimated_kill_time_seconds == pytest.approx(175.0)
    assert assessment.next_horizon_seconds == pytest.approx(175.0)
    assert assessment.selectable is False


def test_converged_140k_projection_is_ready() -> None:
    service = RotationDDParseObjectiveService()
    evidence = RotationDDParseCandidateEvidence(
        candidate_id="candidate-a",
        scorecard=_scorecard(),
        projected_duration_seconds=150.0,
        projected_total_damage=21_000_000.0,
    )

    assessment = service.assess(
        objective=RotationDDParseObjective(),
        evidence=evidence,
    )

    assert assessment.state is RotationDDParseProjectionState.READY
    assert assessment.projected_dps == pytest.approx(140_000.0)
    assert assessment.estimated_kill_time_seconds == pytest.approx(150.0)
    assert assessment.selectable is True


def test_projection_that_is_too_long_requests_shorter_horizon() -> None:
    service = RotationDDParseObjectiveService()
    evidence = RotationDDParseCandidateEvidence(
        candidate_id="candidate-a",
        scorecard=_scorecard(),
        projected_duration_seconds=180.0,
        projected_total_damage=25_200_000.0,
    )

    assessment = service.assess(
        objective=RotationDDParseObjective(),
        evidence=evidence,
    )

    assert assessment.projected_dps == pytest.approx(140_000.0)
    assert assessment.state is RotationDDParseProjectionState.NEEDS_SHORTER_PROJECTION
    assert assessment.next_horizon_seconds == pytest.approx(150.0)
    assert assessment.selectable is False


def test_hard_obligation_failure_blocks_parse_candidate_before_damage_ranking() -> None:
    service = RotationDDParseObjectiveService()
    evidence = RotationDDParseCandidateEvidence(
        candidate_id="illegal-but-huge-damage",
        scorecard=_scorecard(eligible=False),
        projected_duration_seconds=100.0,
        projected_total_damage=30_000_000.0,
    )

    assessment = service.assess(
        objective=RotationDDParseObjective(),
        evidence=evidence,
    )

    assert assessment.state is RotationDDParseProjectionState.INELIGIBLE
    assert assessment.selectable is False
    assert assessment.projected_dps is None


def test_missing_rotation_damage_stays_unresolved_instead_of_becoming_zero_dps() -> None:
    service = RotationDDParseObjectiveService()
    evidence = RotationDDParseCandidateEvidence(
        candidate_id="unknown-damage",
        scorecard=_scorecard(),
        projected_duration_seconds=150.0,
        projected_total_damage=None,
    )

    assessment = service.assess(
        objective=RotationDDParseObjective(),
        evidence=evidence,
    )

    assert assessment.state is RotationDDParseProjectionState.UNRESOLVED
    assert assessment.projected_dps is None
    assert assessment.selectable is False
    assert "projected rotation damage is unavailable" in assessment.reasons


def test_verified_zero_damage_is_known_ineligible_not_unresolved() -> None:
    service = RotationDDParseObjectiveService()
    evidence = RotationDDParseCandidateEvidence(
        candidate_id="zero-damage",
        scorecard=_scorecard(),
        projected_duration_seconds=150.0,
        projected_total_damage=0.0,
    )

    assessment = service.assess(
        objective=RotationDDParseObjective(),
        evidence=evidence,
    )

    assert assessment.state is RotationDDParseProjectionState.INELIGIBLE
    assert assessment.projected_dps == 0.0
    assert assessment.selectable is False


def test_ready_candidates_rank_by_sustainable_projected_dps() -> None:
    service = RotationDDParseObjectiveService()
    objective = RotationDDParseObjective(convergence_tolerance_seconds=0.5)

    slower = service.assess(
        objective=objective,
        evidence=RotationDDParseCandidateEvidence(
            candidate_id="140k",
            scorecard=_scorecard(),
            projected_duration_seconds=150.0,
            projected_total_damage=21_000_000.0,
        ),
    )
    faster = service.assess(
        objective=objective,
        evidence=RotationDDParseCandidateEvidence(
            candidate_id="160k",
            scorecard=_scorecard(),
            projected_duration_seconds=131.25,
            projected_total_damage=21_000_000.0,
        ),
    )
    unresolved = service.assess(
        objective=objective,
        evidence=RotationDDParseCandidateEvidence(
            candidate_id="unknown",
            scorecard=_scorecard(),
            projected_duration_seconds=120.0,
            projected_total_damage=None,
        ),
    )

    ranked = service.rank_ready((slower, unresolved, faster))

    assert [item.candidate_id for item in ranked] == ["160k", "140k"]


def test_invalid_objective_and_projection_values_fail_closed() -> None:
    with pytest.raises(ValueError, match="target health"):
        RotationDDParseObjective(target_health=0)

    with pytest.raises(ValueError, match="projected duration"):
        RotationDDParseCandidateEvidence(
            candidate_id="bad",
            scorecard=_scorecard(),
            projected_duration_seconds=0,
            projected_total_damage=1,
        )
