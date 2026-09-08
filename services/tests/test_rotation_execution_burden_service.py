from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_execution_burden_service import RotationExecutionBurdenService


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def test_execution_burden_counts_explicit_schedule_dimensions_without_weighting_them() -> None:
    plan = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
        RotationAction(1.0, 0, RotationActionKind.LIGHT_ATTACK, None, "front"),
        RotationAction(2.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(3.0, 0, RotationActionKind.HEAVY_ATTACK, None, "back"),
        RotationAction(5.0, 0, RotationActionKind.ULTIMATE, "Aggressive Horn", "back"),
        RotationAction(6.0, 0, RotationActionKind.POTION, "Essence of Spell Power", "back"),
        RotationAction(7.0, 0, RotationActionKind.WAIT, None, "back"),
    )

    burden = RotationExecutionBurdenService().assess(plan)

    assert burden.total_actions == 7
    assert burden.skill_casts == 1
    assert burden.ultimate_casts == 1
    assert burden.light_attacks == 1
    assert burden.heavy_attacks == 1
    assert burden.potions == 1
    assert burden.bar_swaps == 1
    assert burden.waits == 1


def test_execution_burden_compare_exposes_each_delta_independently() -> None:
    baseline = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
        RotationAction(1.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(2.0, 0, RotationActionKind.SKILL, "Energy Orb", "back"),
    )
    candidate = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
        RotationAction(1.0, 0, RotationActionKind.BAR_SWAP, None, "back"),
        RotationAction(2.0, 0, RotationActionKind.SKILL, "Energy Orb", "back"),
        RotationAction(3.0, 0, RotationActionKind.BAR_SWAP, None, "front"),
        RotationAction(4.0, 0, RotationActionKind.HEAVY_ATTACK, None, "front"),
        RotationAction(6.0, 0, RotationActionKind.WAIT, None, "front"),
    )

    delta = RotationExecutionBurdenService().compare(
        baseline_plan=baseline,
        candidate_plan=candidate,
    )

    assert delta.total_actions_delta == 3
    assert delta.skill_casts_delta == 0
    assert delta.ultimate_casts_delta == 0
    assert delta.light_attacks_delta == 0
    assert delta.heavy_attacks_delta == 1
    assert delta.potions_delta == 0
    assert delta.bar_swaps_delta == 1
    assert delta.waits_delta == 1


def test_execution_burden_compare_rejects_different_build_identity() -> None:
    baseline = _plan(
        RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )
    candidate = RotationPlan(
        character_name="Magrat",
        build_name="GH Healer",
        duration_seconds=60.0,
        actions=baseline.actions,
    )

    try:
        RotationExecutionBurdenService().compare(
            baseline_plan=baseline,
            candidate_plan=candidate,
        )
    except ValueError as exc:
        assert "same build" in str(exc)
    else:
        raise AssertionError("expected different build identities to be rejected")
