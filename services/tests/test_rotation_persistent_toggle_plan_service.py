from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_persistent_toggle_plan_service import (
    RotationPersistentTogglePlanService,
)


def _action(time_seconds, sequence, kind, name=None, bar=None):
    return RotationAction(
        time_seconds=float(time_seconds),
        sequence=int(sequence),
        kind=kind,
        name=name,
        bar=bar,
    )


def test_double_barred_magical_banner_is_activated_once_and_recasts_become_fillers() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=6.0,
        actions=(
            _action(0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            _action(0, 1, RotationActionKind.SKILL, "Magical Banner", "front"),
            _action(1, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            _action(1, 1, RotationActionKind.SKILL, "Venom Skull", "front"),
            _action(2, 0, RotationActionKind.BAR_SWAP, bar="back"),
            _action(3, 0, RotationActionKind.LIGHT_ATTACK, bar="back"),
            _action(3, 1, RotationActionKind.SKILL, "Magical Banner", "back"),
            _action(4, 0, RotationActionKind.LIGHT_ATTACK, bar="back"),
            _action(4, 1, RotationActionKind.SKILL, "Resolving Vigor", "back"),
            _action(5, 0, RotationActionKind.BAR_SWAP, bar="front"),
            _action(6, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            _action(6, 1, RotationActionKind.SKILL, "Magical Banner", "front"),
        ),
    )

    result = RotationPersistentTogglePlanService().normalize(plan)

    banner_actions = [
        action
        for action in result.plan.actions
        if action.kind is RotationActionKind.SKILL and action.name == "Magical Banner"
    ]
    assert [(action.time_seconds, action.bar) for action in banner_actions] == [(0.0, "front")]
    assert next(
        action for action in result.plan.actions if action.time_seconds == 3.0 and action.sequence == 1
    ).name == "Resolving Vigor"
    assert next(
        action for action in result.plan.actions if action.time_seconds == 6.0 and action.sequence == 1
    ).name == "Venom Skull"
    assert result.normalized_toggle_names == ("Magical Banner",)
    assert any("activated once and remains active while double-barred" in item for item in result.plan.assumptions)
    assert any("persistent toggle recast of 'Magical Banner' at 3s" in item for item in result.plan.unresolved)


def test_explicit_priorities_order_persistent_toggle_fillers_and_remove_priority_gap() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Priority DD",
        duration_seconds=6.0,
        actions=(
            _action(0, 1, RotationActionKind.SKILL, "Magical Banner", "front"),
            _action(1, 1, RotationActionKind.SKILL, "Lower Priority Filler", "front"),
            _action(2, 1, RotationActionKind.SKILL, "Higher Priority Filler", "front"),
            _action(3, 1, RotationActionKind.SKILL, "Magical Banner", "back"),
            _action(4, 1, RotationActionKind.SKILL, "Back Filler", "back"),
            _action(5, 1, RotationActionKind.SKILL, "Magical Banner", "front"),
        ),
    )
    priorities = AbilityPriorityList(
        character_name="Rylonia",
        build_name="Priority DD",
        role="DD",
        entries=(
            AbilityPriorityEntry("front", 1, "Lower Priority Filler", 20),
            AbilityPriorityEntry("front", 2, "Higher Priority Filler", 5),
            AbilityPriorityEntry("back", 1, "Back Filler", 10),
        ),
    )

    result = RotationPersistentTogglePlanService().normalize(
        plan,
        priorities=priorities,
    )

    assert next(
        action for action in result.plan.actions if action.time_seconds == 3.0 and action.sequence == 1
    ).name == "Back Filler"
    assert next(
        action for action in result.plan.actions if action.time_seconds == 5.0 and action.sequence == 1
    ).name == "Higher Priority Filler"
    assert not any("exact priority ranking is unresolved" in item for item in result.plan.unresolved)
    assert any("explicit-priority same-bar filler 'Higher Priority Filler'" in item for item in result.plan.assumptions)


def test_single_bar_persistent_toggle_fails_closed_without_rewriting_recasts() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Single Bar",
        duration_seconds=2.0,
        actions=(
            _action(0, 1, RotationActionKind.SKILL, "Magical Banner", "front"),
            _action(1, 1, RotationActionKind.SKILL, "Magical Banner", "front"),
        ),
    )

    result = RotationPersistentTogglePlanService().normalize(plan)

    assert [action.name for action in result.plan.actions] == ["Magical Banner", "Magical Banner"]
    assert result.normalized_toggle_names == ()
    assert result.plan.unresolved == (
        "persistent toggle 'Magical Banner' is not represented on both bars; single-bar toggle lifetime across bar swaps is unresolved",
    )
