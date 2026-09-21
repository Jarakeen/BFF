from dataclasses import replace

from models.combat_simulation import (
    CombatSimulationEvent,
    CombatSimulationResult,
    SimulationEventPriority,
)
from services.combat_simulation_deterministic_replay_service import (
    CombatSimulationDeterministicReplayService,
)


def _result(**changes):
    base = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(),
        resources=(),
        effect_windows=(),
        target_state=None,
        unresolved=(),
    )
    return replace(base, **changes)


def test_replay_verifier_accepts_identical_deterministic_results() -> None:
    calls = []

    def runner():
        calls.append(True)
        return _result()

    verification = CombatSimulationDeterministicReplayService().verify(runner)

    assert len(calls) == 2
    assert verification.deterministic is True
    assert verification.differing_signature_fields == ()
    assert verification.first == verification.second


def test_replay_verifier_identifies_signature_field_drift() -> None:
    results = iter(
        (
            _result(),
            _result(final_bar="back", unresolved=("runtime drift",)),
        )
    )

    verification = CombatSimulationDeterministicReplayService().verify(
        lambda: next(results)
    )

    assert verification.deterministic is False
    assert verification.differing_signature_fields == (
        "final_bar",
        "unresolved",
    )


def test_replay_verifier_requires_combat_simulation_result() -> None:
    try:
        CombatSimulationDeterministicReplayService().verify(lambda: object())
    except TypeError as exc:
        assert "CombatSimulationResult" in str(exc)
    else:
        raise AssertionError("Expected invalid replay result to fail closed")



def test_replay_verifier_reports_damage_unresolved_drift() -> None:
    results = iter(
        (
            _result(),
            _result(damage_unresolved=("damage drift",)),
        )
    )

    verification = CombatSimulationDeterministicReplayService().verify(
        lambda: next(results)
    )

    assert verification.deterministic is False
    assert verification.differing_signature_fields == ("damage_unresolved",)


def test_combat_simulation_result_rejects_non_finite_or_negative_duration() -> None:
    for value in (-1.0, float("nan"), float("inf"), float("-inf")):
        try:
            _result(duration_seconds=value)
        except ValueError as exc:
            assert "finite and non-negative" in str(exc)
        else:
            raise AssertionError("Expected invalid simulation result duration to fail closed")


def test_combat_simulation_result_rejects_event_beyond_duration() -> None:
    event = CombatSimulationEvent(
        time_seconds=6.0,
        priority=int(SimulationEventPriority.ACTION),
        sequence=0,
        event_type="action",
        source="Too Late",
    )

    try:
        _result(events=(event,))
    except ValueError as exc:
        assert "beyond its duration" in str(exc)
    else:
        raise AssertionError("Expected post-horizon result event to fail closed")
