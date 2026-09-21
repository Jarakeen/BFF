from __future__ import annotations

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
