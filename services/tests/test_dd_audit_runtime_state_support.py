from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from tools.dd_audit_runtime_state_support import (
    build_plan_attacker_runtime_state_resolver,
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


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.LIGHT_ATTACK,
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Magical Banner",
                bar="front",
            ),
            RotationAction(
                time_seconds=5.0,
                sequence=0,
                kind=RotationActionKind.BAR_SWAP,
                bar="back",
            ),
        ),
    )


def test_audit_runtime_state_respects_ordered_banner_activation() -> None:
    resolve = build_plan_attacker_runtime_state_resolver(
        build=_build(),
        plan=_plan(),
    )

    before = resolve(2.0, 0)
    after = resolve(2.0, 1)

    assert before.resolved is True
    assert before.combat_state is not None
    assert before.combat_state.has_buff("Magical Banner") is False
    assert before.active_bar == "front"

    assert after.resolved is True
    assert after.combat_state is not None
    assert after.combat_state.has_buff("Magical Banner") is True
    assert after.active_bar == "front"


def test_audit_runtime_state_tracks_exact_plan_bar_after_swap() -> None:
    resolve = build_plan_attacker_runtime_state_resolver(
        build=_build(),
        plan=_plan(),
    )

    result = resolve(6.0, 0)

    assert result.resolved is True
    assert result.active_bar == "back"
    assert result.combat_state is not None
    assert result.combat_state.has_buff("Magical Banner") is True


def test_audit_runtime_state_fails_closed_for_unproven_single_bar_toggle() -> None:
    resolve = build_plan_attacker_runtime_state_resolver(
        build=_build(double_barred=False),
        plan=_plan(),
    )

    result = resolve(4.0, 0)

    assert result.resolved is False
    assert result.combat_state is None
    assert "not represented on both bars" in result.unresolved[0]
