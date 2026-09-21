from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_generated_whole_plan_choice_evaluator_service import (
    ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluator,
)


class _Runtime:
    def evaluate(self, build, **kwargs):
        plan = kwargs["plan"]
        return SimpleNamespace(
            record=SimpleNamespace(
                modeled_dps=float(plan.score),
                duration_seconds=float(plan.duration_seconds),
            ),
            mechanic_complete=True,
            unresolved=(),
        )


def test_fixed_witness_evaluator_forwards_plan_and_returns_whole_plan_score() -> None:
    scenario = SimpleNamespace(
        build=object(),
        progression=object(),
        gear_state=object(),
        runtime_snapshot=object(),
        target_health=100000,
        target_resistance=18200.0,
        target_name="Boss",
    )
    choice = SimpleNamespace(
        identity="rotation:3",
        plan=SimpleNamespace(score=123.0, duration_seconds=20.0),
        starting_bar="back",
    )
    evaluator = ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluator(
        runtime_service=_Runtime(),
        scenario=scenario,
        choice_id_resolver=lambda row: row.identity,
        plan_resolver=lambda row: row.plan,
        initial_bar_resolver=lambda row: row.starting_bar,
    )

    result = evaluator.evaluate(choice)

    assert result.choice_id == "rotation:3"
    assert result.modeled_dps == 123.0
    assert result.duration_seconds == 20.0
    assert result.mechanic_complete is True


def test_invalid_initial_bar_is_rejected_before_runtime_evaluation() -> None:
    scenario = SimpleNamespace(
        build=object(),
        progression=object(),
        gear_state=object(),
        runtime_snapshot=object(),
        target_health=100000,
        target_resistance=18200.0,
        target_name="Boss",
    )
    choice = SimpleNamespace(
        identity="bad",
        plan=SimpleNamespace(score=1.0, duration_seconds=10.0),
        starting_bar="middle",
    )
    evaluator = ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluator(
        runtime_service=_Runtime(),
        scenario=scenario,
        choice_id_resolver=lambda row: row.identity,
        plan_resolver=lambda row: row.plan,
        initial_bar_resolver=lambda row: row.starting_bar,
    )

    try:
        evaluator.evaluate(choice)
    except ValueError:
        pass
    else:
        raise AssertionError("expected invalid initial bar to fail")


def test_unresolved_runtime_result_stays_unresolved() -> None:
    class _GapRuntime:
        def evaluate(self, build, **kwargs):
            return SimpleNamespace(
                record=None,
                mechanic_complete=False,
                unresolved=("runtime proc unresolved",),
            )

    scenario = SimpleNamespace(
        build=object(),
        progression=object(),
        gear_state=object(),
        runtime_snapshot=object(),
        target_health=100000,
        target_resistance=18200.0,
        target_name="Boss",
    )
    choice = SimpleNamespace(
        identity="gap",
        plan=SimpleNamespace(duration_seconds=10.0),
        starting_bar="front",
    )
    evaluator = ExtremeSustainedDPSGeneratedWholePlanChoiceEvaluator(
        runtime_service=_GapRuntime(),
        scenario=scenario,
        choice_id_resolver=lambda row: row.identity,
        plan_resolver=lambda row: row.plan,
        initial_bar_resolver=lambda row: row.starting_bar,
    )

    result = evaluator.evaluate(choice)

    assert result.modeled_dps is None
    assert result.mechanic_complete is False
    assert result.unresolved == ("runtime proc unresolved",)
