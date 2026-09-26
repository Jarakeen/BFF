from __future__ import annotations

import pytest

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
    ExtremeSustainedDPSGeneratedBranchAndBoundSearchService,
    ExtremeSustainedDPSGeneratedSearchBranch,
    ExtremeSustainedDPSGeneratedSearchResult,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


def _branch(key, upper, *, safe=True, leaf=False, depth=0, unresolved=()):
    return ExtremeSustainedDPSGeneratedSearchBranch(
        candidate_key=key,
        depth=depth,
        is_leaf=leaf,
        upper_bound=ExtremeSustainedDPSBoundEvidence(
            candidate_key=key,
            upper_bound_dps=upper,
            proven_safe=safe,
            source="test",
            unresolved=tuple(unresolved),
        ),
    )


def _leaf_eval(scores, *, duration=10.0, incomplete=()):
    def evaluate(branch):
        score = scores.get(branch.candidate_key)
        unresolved = ("mechanic gap",) if branch.candidate_key in incomplete else ()
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=branch.candidate_key,
            modeled_dps=score,
            duration_seconds=duration,
            mechanic_complete=branch.candidate_key not in incomplete,
            unresolved=unresolved,
        )
    return evaluate


def test_proven_bound_below_incumbent_prunes_without_exact_leaf_evaluation() -> None:
    roots = (
        _branch("high", 200.0, leaf=True),
        _branch("low", 90.0, leaf=True),
    )
    called = []

    def evaluate(branch):
        called.append(branch.candidate_key)
        score = {"high": 100.0, "low": 80.0}[branch.candidate_key]
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=branch.candidate_key,
            modeled_dps=score,
            duration_seconds=10.0,
            mechanic_complete=True,
        )

    result = ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
        roots,
        expand_branch=lambda _branch: (),
        evaluate_leaf=evaluate,
        required_duration_seconds=10.0,
    )

    assert called == ["high"]
    assert result.pruned_branch_count == 1
    assert result.best_modeled_dps == 100.0
    assert result.global_maximum_proven is True
    assert result.unique_leader_proven is True


def test_equal_bound_remains_open_and_tie_is_preserved() -> None:
    roots = (
        _branch("a", 100.0, leaf=True),
        _branch("b", 100.0, leaf=True),
    )
    result = ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
        roots,
        expand_branch=lambda _branch: (),
        evaluate_leaf=_leaf_eval({"a": 100.0, "b": 100.0}),
        required_duration_seconds=10.0,
    )

    assert result.evaluated_leaf_count == 2
    assert result.best_modeled_dps == 100.0
    assert tuple(row.candidate_key for row in result.best_candidates) == ("a", "b")
    assert result.global_maximum_proven is True
    assert result.unique_leader is None
    assert result.unique_leader_proven is False


def test_missing_bound_forces_branch_open_but_can_still_complete_proof() -> None:
    root = _branch("root", None, safe=False, leaf=False)

    def expand(_branch):
        return (_branch_factory("leaf", None, safe=False, leaf=True, depth=1),)

    def _branch_factory(key, upper, *, safe, leaf, depth):
        return _branch(key, upper, safe=safe, leaf=leaf, depth=depth)

    result = ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
        (root,),
        expand_branch=expand,
        evaluate_leaf=_leaf_eval({"leaf": 77.0}),
        required_duration_seconds=10.0,
    )

    assert result.forced_open_branch_count == 2
    assert result.best_modeled_dps == 77.0
    assert result.global_maximum_proven is True


def test_incomplete_leaf_blocks_global_maximum_proof() -> None:
    roots = (
        _branch("good", 100.0, leaf=True),
        _branch("gap", None, safe=False, leaf=True),
    )
    result = ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
        roots,
        expand_branch=lambda _branch: (),
        evaluate_leaf=_leaf_eval(
            {"good": 100.0, "gap": None},
            incomplete=("gap",),
        ),
        required_duration_seconds=10.0,
    )

    assert result.best_modeled_dps == 100.0
    assert result.global_maximum_proven is False
    assert result.unresolved


def test_mismatched_leaf_horizon_blocks_global_proof() -> None:
    result = ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
        (_branch("leaf", 100.0, leaf=True),),
        expand_branch=lambda _branch: (),
        evaluate_leaf=_leaf_eval({"leaf": 90.0}, duration=9.0),
        required_duration_seconds=10.0,
    )

    assert result.global_maximum_proven is False
    assert any("required search horizon" in row for row in result.unresolved)


def test_duplicate_branch_identity_is_blocking_evidence() -> None:
    roots = (
        _branch("same", 100.0, leaf=True),
        _branch("same", 100.0, leaf=True),
    )
    result = ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
        roots,
        expand_branch=lambda _branch: (),
        evaluate_leaf=_leaf_eval({"same": 50.0}),
        required_duration_seconds=10.0,
    )

    assert result.global_maximum_proven is False
    assert any("Duplicate generated search branch identity" in row for row in result.unresolved)

def test_forced_open_bound_diagnostic_does_not_poison_exact_leaf_proof() -> None:
    result = ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
        (
            _branch(
                "leaf",
                None,
                safe=False,
                leaf=True,
                unresolved=("optimistic action ceiling is unavailable",),
            ),
        ),
        expand_branch=lambda _branch: (),
        evaluate_leaf=_leaf_eval({"leaf": 88.0}),
        required_duration_seconds=10.0,
    )

    assert result.forced_open_branch_count == 1
    assert result.best_modeled_dps == 88.0
    assert result.global_maximum_proven is True
    assert result.unresolved == ()



def test_generated_branch_requires_strict_depth_and_leaf_flag() -> None:
    bound = ExtremeSustainedDPSBoundEvidence(
        candidate_key="branch",
        upper_bound_dps=100.0,
        proven_safe=True,
        source="test",
    )

    with pytest.raises(TypeError, match="depth must be an integer"):
        ExtremeSustainedDPSGeneratedSearchBranch(
            candidate_key="branch",
            depth=True,
            is_leaf=False,
            upper_bound=bound,
        )

    with pytest.raises(TypeError, match="is_leaf must be boolean"):
        ExtremeSustainedDPSGeneratedSearchBranch(
            candidate_key="branch",
            depth=0,
            is_leaf=1,
            upper_bound=bound,
        )


@pytest.mark.parametrize("value", (float("nan"), float("inf"), -1.0))
def test_exact_leaf_rejects_invalid_modeled_dps(value) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key="leaf",
            modeled_dps=value,
            duration_seconds=10.0,
            mechanic_complete=True,
        )


def test_generated_search_result_rejects_leaf_count_drift() -> None:
    leaf = ExtremeSustainedDPSExactLeafEvaluation(
        candidate_key="leaf",
        modeled_dps=10.0,
        duration_seconds=10.0,
        mechanic_complete=True,
    )

    with pytest.raises(
        ValueError,
        match="evaluated_leaf_count must equal evaluated_leaves length",
    ):
        ExtremeSustainedDPSGeneratedSearchResult(
            best_modeled_dps=10.0,
            best_candidates=(leaf,),
            unique_leader=leaf,
            evaluated_leaves=(leaf,),
            visited_branch_count=1,
            expanded_branch_count=0,
            evaluated_leaf_count=2,
            pruned_branch_count=0,
            forced_open_branch_count=0,
            global_maximum_proven=True,
            unique_leader_proven=True,
            evidence=(),
            unresolved=(),
        )


def test_generated_search_rejects_nonfinite_duration_input() -> None:
    with pytest.raises(ValueError, match="duration must be finite and positive"):
        ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
            (_branch("leaf", 10.0, leaf=True),),
            expand_branch=lambda _branch: (),
            evaluate_leaf=_leaf_eval({"leaf": 10.0}),
            required_duration_seconds=float("nan"),
        )


def test_generated_search_result_rejects_duplicate_evaluated_leaf_keys() -> None:
    a = ExtremeSustainedDPSExactLeafEvaluation(
        candidate_key="same",
        modeled_dps=10.0,
        duration_seconds=10.0,
        mechanic_complete=True,
    )
    b = ExtremeSustainedDPSExactLeafEvaluation(
        candidate_key="same",
        modeled_dps=9.0,
        duration_seconds=10.0,
        mechanic_complete=True,
    )

    with pytest.raises(ValueError, match="evaluated_leaves must have unique candidate keys"):
        ExtremeSustainedDPSGeneratedSearchResult(
            best_modeled_dps=10.0,
            best_candidates=(a,),
            unique_leader=a,
            evaluated_leaves=(a, b),
            visited_branch_count=2,
            expanded_branch_count=0,
            evaluated_leaf_count=2,
            pruned_branch_count=0,
            forced_open_branch_count=0,
            global_maximum_proven=True,
            unique_leader_proven=True,
            evidence=(),
            unresolved=(),
        )


def test_generated_search_result_unique_proof_requires_exactly_one_best_candidate() -> None:
    a = ExtremeSustainedDPSExactLeafEvaluation(
        candidate_key="a",
        modeled_dps=10.0,
        duration_seconds=10.0,
        mechanic_complete=True,
    )
    b = ExtremeSustainedDPSExactLeafEvaluation(
        candidate_key="b",
        modeled_dps=10.0,
        duration_seconds=10.0,
        mechanic_complete=True,
    )

    with pytest.raises(ValueError, match="exactly one best candidate"):
        ExtremeSustainedDPSGeneratedSearchResult(
            best_modeled_dps=10.0,
            best_candidates=(a, b),
            unique_leader=a,
            evaluated_leaves=(a, b),
            visited_branch_count=2,
            expanded_branch_count=0,
            evaluated_leaf_count=2,
            pruned_branch_count=0,
            forced_open_branch_count=0,
            global_maximum_proven=True,
            unique_leader_proven=True,
            evidence=(),
            unresolved=(),
        )


def test_generated_search_requires_tuple_roots() -> None:
    with pytest.raises(TypeError, match="roots must be a tuple"):
        ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
            [_branch("leaf", 10.0, leaf=True)],
            expand_branch=lambda _branch: (),
            evaluate_leaf=_leaf_eval({"leaf": 10.0}),
            required_duration_seconds=10.0,
        )


def test_generated_search_requires_canonical_exact_leaf_evidence() -> None:
    with pytest.raises(TypeError, match="canonical exact evidence"):
        ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
            (_branch("leaf", 10.0, leaf=True),),
            expand_branch=lambda _branch: (),
            evaluate_leaf=lambda branch: type(
                "Leaf",
                (),
                {
                    "candidate_key": branch.candidate_key,
                    "modeled_dps": 10.0,
                    "duration_seconds": 10.0,
                    "mechanic_complete": True,
                    "unresolved": (),
                },
            )(),
            required_duration_seconds=10.0,
        )


def test_generated_search_requires_tuple_child_branches() -> None:
    root = _branch("root", 20.0, leaf=False)

    with pytest.raises(TypeError, match="branch expander must return a tuple"):
        ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
            (root,),
            expand_branch=lambda _parent: [_branch("leaf", 10.0, leaf=True, depth=1)],
            evaluate_leaf=_leaf_eval({"leaf": 10.0}),
            required_duration_seconds=10.0,
        )


def test_exact_leaf_requires_tuple_evidence_collections() -> None:
    with pytest.raises(TypeError, match="evidence must be a tuple"):
        ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key="leaf",
            modeled_dps=10.0,
            duration_seconds=10.0,
            mechanic_complete=True,
            evidence=["mutable"],
        )
