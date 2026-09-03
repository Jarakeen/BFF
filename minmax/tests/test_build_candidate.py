import pytest

from minmax.build_candidate import (
    BuildCandidate,
    BuildChange,
    CandidateEvaluationState,
)
from models.build_model import PlayerBuild


def test_candidate_snapshots_build_without_mutating_saved_build_reference():
    saved_build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Mundus="The Ritual")
    change = BuildChange.from_values(
        path="Mundus",
        before="The Ritual",
        after="The Thief",
        source="phase12:test",
    )
    proposed_build = PlayerBuild.from_dict(saved_build.to_dict())
    proposed_build.Mundus = "The Thief"

    candidate = BuildCandidate.from_build(
        character_id="magrat-id",
        baseline_build_id="df-healer-id",
        candidate_id="mundus-thief",
        candidate_build=proposed_build,
        changes=(change,),
        candidate_source="bounded_mundus_swap",
    )

    proposed_build.Mundus = "The Atronach"
    reconstructed = candidate.candidate_build

    assert saved_build.Mundus == "The Ritual"
    assert reconstructed.Mundus == "The Thief"
    assert candidate.changes == (change,)
    assert change.before == "The Ritual"
    assert change.after == "The Thief"
    assert candidate.is_evaluable is True


def test_candidate_returns_fresh_build_for_each_downstream_evaluation():
    candidate = BuildCandidate.from_build(
        character_id="magrat-id",
        baseline_build_id="df-healer-id",
        candidate_id="baseline-copy",
        candidate_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        changes=(),
        candidate_source="phase12:test",
    )

    first = candidate.candidate_build
    first.BuildName = "mutated evaluator copy"

    assert candidate.candidate_build.BuildName == "DF Healer"


def test_unknown_candidate_preserves_unresolved_evidence():
    candidate = BuildCandidate.from_build(
        character_id="magrat-id",
        baseline_build_id="df-healer-id",
        candidate_id="unknown-sustain",
        candidate_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
        changes=(),
        candidate_source="phase12:test",
        evaluation_state=CandidateEvaluationState.UNKNOWN,
        unresolved=("candidate sustain cannot be evaluated",),
    )

    assert candidate.is_evaluable is False
    assert candidate.unresolved == ("candidate sustain cannot be evaluated",)


def test_evaluable_candidate_cannot_hide_unresolved_evidence():
    with pytest.raises(ValueError, match="cannot carry unresolved evidence"):
        BuildCandidate.from_build(
            character_id="magrat-id",
            baseline_build_id="df-healer-id",
            candidate_id="bad-state",
            candidate_build=PlayerBuild(Name="Magrat", BuildName="DF Healer"),
            changes=(),
            candidate_source="phase12:test",
            unresolved=("coverage unknown",),
        )


def test_build_change_requires_provenance_source():
    with pytest.raises(ValueError, match="source is required"):
        BuildChange.from_values(
            path="Mundus",
            before="The Ritual",
            after="The Thief",
            source="",
        )
