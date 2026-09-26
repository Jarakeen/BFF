from __future__ import annotations

import pytest

from services.extreme_sustained_dps_finite_whole_plan_dominance_service import (
    ExtremeSustainedDPSFiniteWholePlanDominanceService,
    ExtremeSustainedDPSWholePlanEvaluation,
)


class _Frontier:
    axes = ("rotation_order", "light_attack_weave")
    choice_count = 3
    denominator_proven = True
    omitted_scope = ("Ultimate policy remains separate",)

    def choice_at(self, index):
        return index


class _Evaluator:
    def __init__(self, rows):
        self.rows = rows

    def evaluate(self, choice):
        return self.rows[choice]


def _row(choice_id, dps, *, duration=10.0, complete=True, unresolved=()):
    return ExtremeSustainedDPSWholePlanEvaluation(
        choice_id=choice_id,
        modeled_dps=dps,
        duration_seconds=duration,
        mechanic_complete=complete,
        unresolved=tuple(unresolved),
    )


def test_complete_same_horizon_family_promotes_axes_and_dps_ceiling() -> None:
    result = ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
        candidate_key="branch:rotation",
        frontier=_Frontier(),
        evaluator=_Evaluator(
            {
                0: _row("r0", 100.0),
                1: _row("r1", 140.0),
                2: _row("r2", 120.0),
            }
        ),
        required_duration_seconds=10.0,
        source="finite rotation family",
    )

    assert result.axis_coverage.dominated_axes == (
        "rotation_order",
        "light_attack_weave",
    )
    assert result.bound.proven_safe is True
    assert result.upper_bound_dps == 140.0
    assert result.winning_choice_id == "r1"
    assert result.omitted_scope == ("Ultimate policy remains separate",)
    assert result.axis_coverage.omitted_scope == result.omitted_scope


def test_plan_shape_may_differ_when_whole_plan_scores_share_horizon() -> None:
    result = ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
        candidate_key="branch:policy",
        frontier=_Frontier(),
        evaluator=_Evaluator(
            {
                0: _row("skill-plan", 90.0),
                1: _row("heavy-plan", 110.0),
                2: _row("ultimate-plan", 105.0),
            }
        ),
        required_duration_seconds=10.0,
        source="finite policy family",
    )

    assert result.bound.upper_bound_dps == 110.0
    assert result.bound.proven_safe is True


def test_mismatched_horizon_blocks_family_ceiling() -> None:
    result = ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
        candidate_key="branch:horizon",
        frontier=_Frontier(),
        evaluator=_Evaluator(
            {
                0: _row("r0", 100.0),
                1: _row("r1", 140.0, duration=9.0),
                2: _row("r2", 120.0),
            }
        ),
        required_duration_seconds=10.0,
        source="finite rotation family",
    )

    assert result.bound.proven_safe is False
    assert result.upper_bound_dps is None
    assert any("required horizon" in row for row in result.unresolved)


def test_incomplete_mechanics_block_family_ceiling() -> None:
    result = ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
        candidate_key="branch:gap",
        frontier=_Frontier(),
        evaluator=_Evaluator(
            {
                0: _row("r0", 100.0),
                1: _row("r1", None, complete=False, unresolved=("proc unresolved",)),
                2: _row("r2", 120.0),
            }
        ),
        required_duration_seconds=10.0,
        source="finite rotation family",
    )

    assert result.axis_coverage.dominated_axes == ()
    assert result.bound.proven_safe is False
    assert any("proc unresolved" in row for row in result.unresolved)


def test_unproven_denominator_blocks_family_ceiling() -> None:
    class _OpenFrontier(_Frontier):
        denominator_proven = False

    result = ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
        candidate_key="branch:open",
        frontier=_OpenFrontier(),
        evaluator=_Evaluator(
            {
                0: _row("r0", 100.0),
                1: _row("r1", 110.0),
                2: _row("r2", 120.0),
            }
        ),
        required_duration_seconds=10.0,
        source="open family",
    )

    assert result.bound.proven_safe is False
    assert any("not proven complete" in row for row in result.unresolved)


def test_whole_plan_frontier_rejects_truthy_denominator_proof() -> None:
    class _BadFrontier(_Frontier):
        denominator_proven = "true"

    with pytest.raises(TypeError, match="denominator_proven must be boolean"):
        ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
            candidate_key="branch:strict-proof",
            frontier=_BadFrontier(),
            evaluator=_Evaluator(
                {
                    0: _row("r0", 100.0),
                    1: _row("r1", 110.0),
                    2: _row("r2", 120.0),
                }
            ),
            required_duration_seconds=10.0,
            source="strict whole-plan boundary",
        )


def test_whole_plan_frontier_rejects_boolean_choice_count() -> None:
    class _BadFrontier(_Frontier):
        choice_count = True

    with pytest.raises(TypeError, match="choice_count must be an integer"):
        ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
            candidate_key="branch:strict-count",
            frontier=_BadFrontier(),
            evaluator=_Evaluator({0: _row("r0", 100.0)}),
            required_duration_seconds=10.0,
            source="strict whole-plan boundary",
        )


def test_whole_plan_frontier_rejects_non_tuple_axes_and_omitted_scope() -> None:
    class _BadAxes(_Frontier):
        axes = ["rotation_order"]

    with pytest.raises(TypeError, match="axes must be a tuple"):
        ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
            candidate_key="branch:strict-axes",
            frontier=_BadAxes(),
            evaluator=_Evaluator(
                {
                    0: _row("r0", 100.0),
                    1: _row("r1", 110.0),
                    2: _row("r2", 120.0),
                }
            ),
            required_duration_seconds=10.0,
            source="strict whole-plan boundary",
        )

    class _BadOmitted(_Frontier):
        omitted_scope = ["open"]

    with pytest.raises(TypeError, match="omitted_scope must be a tuple"):
        ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
            candidate_key="branch:strict-omitted",
            frontier=_BadOmitted(),
            evaluator=_Evaluator(
                {
                    0: _row("r0", 100.0),
                    1: _row("r1", 110.0),
                    2: _row("r2", 120.0),
                }
            ),
            required_duration_seconds=10.0,
            source="strict whole-plan boundary",
        )


def test_whole_plan_duration_rejects_boolean() -> None:
    with pytest.raises(TypeError, match="duration must be numeric"):
        ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
            candidate_key="branch:strict-duration",
            frontier=_Frontier(),
            evaluator=_Evaluator(
                {
                    0: _row("r0", 100.0),
                    1: _row("r1", 110.0),
                    2: _row("r2", 120.0),
                }
            ),
            required_duration_seconds=True,
            source="strict whole-plan boundary",
        )


def test_whole_plan_evaluation_requires_strict_mechanic_proof_and_numeric_fields() -> None:
    with pytest.raises(TypeError, match="mechanic_complete must be boolean"):
        ExtremeSustainedDPSWholePlanEvaluation(
            choice_id="bad-proof",
            modeled_dps=100.0,
            duration_seconds=10.0,
            mechanic_complete="true",
        )

    with pytest.raises(TypeError, match="modeled_dps must be numeric or None"):
        ExtremeSustainedDPSWholePlanEvaluation(
            choice_id="bad-score",
            modeled_dps=True,
            duration_seconds=10.0,
            mechanic_complete=True,
        )

    with pytest.raises(TypeError, match="duration_seconds must be numeric or None"):
        ExtremeSustainedDPSWholePlanEvaluation(
            choice_id="bad-duration",
            modeled_dps=100.0,
            duration_seconds=False,
            mechanic_complete=True,
        )
