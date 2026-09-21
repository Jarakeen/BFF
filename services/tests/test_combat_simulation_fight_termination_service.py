from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.combat_simulation_fight_termination_service import (
    CombatSimulationFightTerminationService,
)


def _plan():
    return RotationPlan(
        character_name="Damage Tester",
        build_name="DD Build",
        duration_seconds=10.0,
        actions=(
            RotationAction(1.0, 0, RotationActionKind.SKILL, name="One", bar="front"),
            RotationAction(2.0, 0, RotationActionKind.SKILL, name="Killer", bar="front"),
            RotationAction(2.0, 1, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(3.0, 0, RotationActionKind.SKILL, name="Too Late", bar="front"),
        ),
        assumptions=("planned horizon",),
    )


def test_fight_termination_truncates_after_exact_killing_action() -> None:
    result = CombatSimulationFightTerminationService().truncate(
        _plan(),
        time_seconds=2.0,
        sequence=0,
    )

    assert result.duration_seconds == 2.0
    assert [(a.time_seconds, a.sequence, a.name) for a in result.actions] == [
        (1.0, 0, "One"),
        (2.0, 0, "Killer"),
    ]
    assert "planned horizon" in result.assumptions
    assert any("target defeated" in value for value in result.assumptions)


def test_fight_termination_rejects_point_after_plan_horizon() -> None:
    try:
        CombatSimulationFightTerminationService().truncate(
            _plan(),
            time_seconds=11.0,
            sequence=0,
        )
    except ValueError as exc:
        assert "exceed plan duration" in str(exc)
    else:
        raise AssertionError("Expected out-of-horizon termination to fail")
