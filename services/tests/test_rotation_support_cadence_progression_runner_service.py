from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_support_cadence_progression_runner_service import (
    RotationSupportCadenceProgressionRunnerService,
    RotationSupportCadenceProgressionStopReason,
)


def _plan(skill_name: str, *, assumptions=(), unresolved=()) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name=skill_name,
                bar="front",
            ),
        ),
        assumptions=tuple(assumptions),
        unresolved=tuple(unresolved),
    )


class _Stepper:
    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []

    def step(self, **kwargs):
        self.calls.append(kwargs)
        if not self.steps:
            raise AssertionError("runner requested more steps than test supplied")
        return self.steps.pop(0)


def _step(*, current, next_plan, next_sustain, advanced=True, unresolved=()):
    return SimpleNamespace(
        seed_plan=current,
        next_seed_plan=next_plan,
        next_seed_sustain=next_sustain,
        advanced=advanced,
        unresolved=tuple(unresolved),
    )


def test_runs_promotions_until_next_step_has_no_promotion() -> None:
    p0 = _plan("Combat Prayer")
    p1 = _plan("Energy Orb")
    p2 = _plan("Budding Seeds")
    s0, s1, s2 = object(), object(), object()
    stepper = _Stepper(
        [
            _step(current=p0, next_plan=p1, next_sustain=s1),
            _step(current=p1, next_plan=p2, next_sustain=s2),
            _step(current=p2, next_plan=p2, next_sustain=s2, advanced=False),
        ]
    )
    runner = RotationSupportCadenceProgressionRunnerService(stepper)
    requirement = object()
    passive = object()

    result = runner.run(
        build=object(),  # type: ignore[arg-type]
        seed_plan=p0,
        seed_sustain=s0,  # type: ignore[arg-type]
        obligations=(),
        effect_uptime_requirements=(requirement,),  # type: ignore[arg-type]
        passives=(passive,),  # type: ignore[arg-type]
        character_id="magrat-id",
        max_iterations=8,
    )

    assert result.final_plan is p2
    assert result.final_sustain is s2
    assert result.stop_reason is RotationSupportCadenceProgressionStopReason.NO_PROMOTION
    assert result.iterations == 3
    assert result.advanced_steps == 2
    assert [call["seed_plan"] for call in stepper.calls] == [p0, p1, p2]
    assert [call["seed_sustain"] for call in stepper.calls] == [s0, s1, s2]
    assert all(call["effect_uptime_requirements"] == (requirement,) for call in stepper.calls)
    assert all(call["passives"] == (passive,) for call in stepper.calls)
    assert all(call["character_id"] == "magrat-id" for call in stepper.calls)


def test_repeated_schedule_is_not_reaccepted() -> None:
    p0 = _plan("Combat Prayer")
    p1 = _plan("Energy Orb")
    s0, s1, s_cycle = object(), object(), object()
    stepper = _Stepper(
        [
            _step(current=p0, next_plan=p1, next_sustain=s1),
            _step(current=p1, next_plan=p0, next_sustain=s_cycle),
        ]
    )
    runner = RotationSupportCadenceProgressionRunnerService(stepper)

    result = runner.run(
        build=object(),  # type: ignore[arg-type]
        seed_plan=p0,
        seed_sustain=s0,  # type: ignore[arg-type]
        obligations=(),
    )

    assert result.stop_reason is RotationSupportCadenceProgressionStopReason.REPEATED_PLAN
    assert result.iterations == 2
    assert result.final_plan is p1
    assert result.final_sustain is s1


def test_schedule_repetition_ignores_provenance_only_changes() -> None:
    p0 = _plan("Combat Prayer")
    same_schedule = _plan(
        "Combat Prayer",
        assumptions=("new scheduler provenance",),
        unresolved=("new diagnostic",),
    )
    s0, s1 = object(), object()
    stepper = _Stepper(
        [_step(current=p0, next_plan=same_schedule, next_sustain=s1)]
    )
    runner = RotationSupportCadenceProgressionRunnerService(stepper)

    result = runner.run(
        build=object(),  # type: ignore[arg-type]
        seed_plan=p0,
        seed_sustain=s0,  # type: ignore[arg-type]
        obligations=(),
    )

    assert result.stop_reason is RotationSupportCadenceProgressionStopReason.REPEATED_PLAN
    assert result.final_plan is p0
    assert result.final_sustain is s0


def test_max_iteration_cap_accepts_last_unique_promotion() -> None:
    p0 = _plan("Combat Prayer")
    p1 = _plan("Energy Orb")
    p2 = _plan("Budding Seeds")
    s0, s1, s2 = object(), object(), object()
    stepper = _Stepper(
        [
            _step(current=p0, next_plan=p1, next_sustain=s1),
            _step(current=p1, next_plan=p2, next_sustain=s2),
        ]
    )
    runner = RotationSupportCadenceProgressionRunnerService(stepper)

    result = runner.run(
        build=object(),  # type: ignore[arg-type]
        seed_plan=p0,
        seed_sustain=s0,  # type: ignore[arg-type]
        obligations=(),
        max_iterations=2,
    )

    assert result.stop_reason is RotationSupportCadenceProgressionStopReason.MAX_ITERATIONS
    assert result.iterations == 2
    assert result.final_plan is p2
    assert result.final_sustain is s2


def test_run_dedupes_unresolved_evidence_across_steps() -> None:
    p0 = _plan("Combat Prayer")
    p1 = _plan("Energy Orb")
    s0, s1 = object(), object()
    stepper = _Stepper(
        [
            _step(
                current=p0,
                next_plan=p1,
                next_sustain=s1,
                unresolved=("duration unresolved", "shared note"),
            ),
            _step(
                current=p1,
                next_plan=p1,
                next_sustain=s1,
                advanced=False,
                unresolved=("SHARED NOTE", "target state unresolved"),
            ),
        ]
    )
    runner = RotationSupportCadenceProgressionRunnerService(stepper)

    result = runner.run(
        build=object(),  # type: ignore[arg-type]
        seed_plan=p0,
        seed_sustain=s0,  # type: ignore[arg-type]
        obligations=(),
    )

    assert result.unresolved == (
        "duration unresolved",
        "shared note",
        "target state unresolved",
    )


def test_max_iterations_must_be_positive() -> None:
    runner = RotationSupportCadenceProgressionRunnerService(_Stepper([]))

    with pytest.raises(ValueError, match="max_iterations must be positive"):
        runner.run(
            build=object(),  # type: ignore[arg-type]
            seed_plan=_plan("Combat Prayer"),
            seed_sustain=object(),  # type: ignore[arg-type]
            obligations=(),
            max_iterations=0,
        )
