from types import SimpleNamespace

import pytest

from models.build_model import PlayerBuild
from minmax.build_candidate_provider_scope import BuildCandidateProviderScope
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _audit(member_id: str, build_name: str) -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name=member_id.title(),
        build_name=build_name,
        character_id=member_id,
        resolved_sources=(),
        resolved_effects=(),
        conditional_sources=(),
        unresolved=(),
        capability_unresolved=(),
        boundaries=(),
    )


class _CapabilityService:
    def audit_build(self, build: PlayerBuild) -> SavedBuildCapabilityAudit:
        return _audit(str(build.Name), str(build.BuildName))


class _RosterEvaluator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[tuple[str, str], ...]]] = []

    def evaluate_saved_build_audits(self, encounter_id, audits):
        snapshot = tuple((audit.character_id, audit.build_name) for audit in audits)
        self.calls.append((encounter_id, snapshot))
        return SimpleNamespace(snapshot=snapshot)


class _CandidateService:
    def candidates(self, report, audits):
        return (report.snapshot,)


class _AssignmentService:
    def assign(self, candidate_sets):
        return tuple(candidate_sets)


def _build(member_id: str, build_name: str) -> PlayerBuild:
    return PlayerBuild(Name=member_id, BuildName=build_name)


def _scope(roster_builds, member_id="magrat"):
    evaluator = _RosterEvaluator()
    scope = BuildCandidateProviderScope.create(
        encounter_id="oaxiltso",
        member_id=member_id,
        roster_builds=tuple(roster_builds),
        capability_service=_CapabilityService(),
        roster_evaluator=evaluator,
        candidate_service=_CandidateService(),
        assignment_service=_AssignmentService(),
    )
    return scope, evaluator


def test_provider_scope_computes_baseline_from_exact_saved_roster() -> None:
    scope, evaluator = _scope(
        (
            _build("magrat", "DF Healer"),
            _build("susan", "Necro Tank"),
        )
    )

    assert scope.baseline_assignments == (
        (("magrat", "DF Healer"), ("susan", "Necro Tank")),
    )
    assert evaluator.calls == [
        (
            "oaxiltso",
            (("magrat", "DF Healer"), ("susan", "Necro Tank")),
        )
    ]


def test_candidate_replaces_only_selected_member_and_preserves_roster_order() -> None:
    scope, evaluator = _scope(
        (
            _build("magrat", "DF Healer"),
            _build("susan", "Necro Tank"),
        )
    )

    assignments = scope.assignments_for(_build("magrat", "DF Healer Candidate"))

    assert assignments == (
        (("magrat", "DF Healer Candidate"), ("susan", "Necro Tank")),
    )
    assert evaluator.calls[-1] == (
        "oaxiltso",
        (("magrat", "DF Healer Candidate"), ("susan", "Necro Tank")),
    )


def test_provider_scope_rejects_duplicate_saved_member_identity() -> None:
    with pytest.raises(ValueError, match="exactly one authoritative build per member"):
        _scope(
            (
                _build("magrat", "DF Healer"),
                _build("magrat", "Alternate Healer"),
            )
        )


def test_provider_scope_rejects_target_member_absent_from_roster() -> None:
    with pytest.raises(ValueError, match="is not present in the saved roster"):
        _scope((_build("susan", "Necro Tank"),), member_id="magrat")


def test_provider_scope_rejects_candidate_identity_drift() -> None:
    scope, _ = _scope(
        (
            _build("magrat", "DF Healer"),
            _build("susan", "Necro Tank"),
        )
    )

    with pytest.raises(ValueError, match="candidate provider identity changed"):
        scope.assignments_for(_build("susan", "Not Magrat"))


def test_provider_scope_is_deterministic_for_identical_candidate_inputs() -> None:
    scope, _ = _scope(
        (
            _build("magrat", "DF Healer"),
            _build("susan", "Necro Tank"),
        )
    )
    candidate = _build("magrat", "DF Healer Candidate")

    first = scope.assignments_for(candidate)
    second = scope.assignments_for(candidate)

    assert first == second
