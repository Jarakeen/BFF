from minmax.combat_damage_modifiers import damage_done_from_combat_state
from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.rotation_plan_persistent_toggle_combat_state_service import (
    RotationPlanPersistentToggleCombatStateService,
)


def _build(*, double_barred: bool = True) -> PlayerBuild:
    return PlayerBuild(
        Name="Rylonia",
        BuildName="Corpsebuster DD",
        Role="DD",
        FrontBarSkills=["Magical Banner", "Venom Skull", "", "", "", ""],
        BackBarSkills=(
            ["Magical Banner", "Stampede", "", "", "", ""]
            if double_barred
            else ["Stampede", "", "", "", "", ""]
        ),
    )


def _plan(*, activations=((2.0, 1, "front"),)) -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=10.0,
        actions=tuple(
            RotationAction(
                time_seconds=time_seconds,
                sequence=sequence,
                kind=RotationActionKind.SKILL,
                name="Magical Banner",
                bar=bar,
            )
            for time_seconds, sequence, bar in activations
        ),
    )


def test_double_barred_banner_is_inactive_before_ordered_activation_and_active_after() -> None:
    service = RotationPlanPersistentToggleCombatStateService()
    build = _build()
    plan = _plan()

    before = service.resolve(
        build,
        plan=plan,
        time_seconds=2.0,
        sequence=0,
    )
    at_activation = service.resolve(
        build,
        plan=plan,
        time_seconds=2.0,
        sequence=1,
    )
    later = service.resolve(
        build,
        plan=plan,
        time_seconds=7.0,
    )

    assert before.resolved is True
    assert before.combat_state is not None
    assert before.combat_state.has_buff("Magical Banner") is False

    assert at_activation.resolved is True
    assert at_activation.combat_state is not None
    assert at_activation.combat_state.has_buff("Magical Banner") is True
    assert at_activation.active_toggle_names == ("Magical Banner",)

    assert later.resolved is True
    assert later.combat_state is not None
    assert later.combat_state.has_buff("Magical Banner") is True


def test_banner_runtime_state_preserves_existing_combat_state_and_routes_magic_only() -> None:
    service = RotationPlanPersistentToggleCombatStateService()
    result = service.resolve(
        _build(),
        plan=_plan(activations=((0.0, 1, "front"),)),
        time_seconds=4.0,
        base_combat_state=CombatState(
            in_combat=True,
            active_buffs=("Minor Berserk",),
        ),
    )

    assert result.resolved is True
    assert result.combat_state is not None
    assert result.combat_state.in_combat is True
    assert result.combat_state.has_buff("Minor Berserk") is True
    assert result.combat_state.has_buff("Magical Banner") is True

    modifiers = damage_done_from_combat_state(result.combat_state)
    assert modifiers.generic == 0.05
    assert modifiers.magic == 0.06
    assert modifiers.physical == 0.0
    assert modifiers.poison == 0.0


def test_single_bar_banner_lifetime_fails_closed_across_bar_swaps() -> None:
    result = RotationPlanPersistentToggleCombatStateService().resolve(
        _build(double_barred=False),
        plan=_plan(),
        time_seconds=5.0,
    )

    assert result.resolved is False
    assert result.combat_state is None
    assert result.unresolved == (
        "persistent toggle 'Magical Banner' is not represented on both bars; runtime lifetime across bar swaps is unresolved",
    )


def test_multiple_final_plan_banner_activations_fail_closed_instead_of_guessing_toggle_state() -> None:
    result = RotationPlanPersistentToggleCombatStateService().resolve(
        _build(),
        plan=_plan(activations=((0.0, 1, "front"), (5.0, 1, "back"))),
        time_seconds=7.0,
    )

    assert result.resolved is False
    assert result.combat_state is None
    assert result.unresolved == (
        "persistent toggle 'Magical Banner' has 2 final-plan activations; toggle on/off state is unresolved",
    )
