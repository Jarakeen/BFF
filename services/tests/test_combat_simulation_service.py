from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from models.effective_build_snapshot import EffectiveBuildSnapshot
from models.combat_simulation import CombatSimulationResourceResult
from services.combat_simulation_healing_service import CombatSimulationHealingProjection
from services.combat_simulation_resource_service import CombatSimulationResourceProjection
from services.combat_simulation_service import CombatSimulationService
from services.combat_simulation_skill_effect_service import CombatSimulationEffectProjection






class _NoopSkillEffectService:
    def project(self, **_kwargs):
        return CombatSimulationEffectProjection(events=(), windows=(), unresolved=())


class _NoopHealingService:
    def project(self, **_kwargs):
        return CombatSimulationHealingProjection(events=(), unresolved=())


class _NoopResourceService:
    def project(self, **_kwargs):
        return CombatSimulationResourceProjection(
            result=CombatSimulationResourceResult(
                resource="magicka",
                starting_amount=0,
                ending_amount=0,
                total_shortfall=0,
            ),
            events=(),
            unresolved=(),
        )


def _service() -> CombatSimulationService:
    return CombatSimulationService(
        resource_service=_NoopResourceService(),
        healing_service=_NoopHealingService(),
        skill_effect_service=_NoopSkillEffectService(),
    )


def _snapshot() -> EffectiveBuildSnapshot:
    return EffectiveBuildSnapshot.from_saved_build(
        PlayerBuild(
            Name="Magrat",
            Gamertag="@keen",
            BuildName="DF Healer",
            EsoClass="Warden",
            Role="Healer",
        ),
        character_id="character-magrat",
        provenance=("phase14 healer control",),
    )


def _healer_plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=6.0,
        actions=(
            RotationAction(
                time_seconds=0.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.LIGHT_ATTACK,
                bar="front",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=0,
                kind=RotationActionKind.BAR_SWAP,
                bar="back",
            ),
            RotationAction(
                time_seconds=2.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name="Illustrious Healing",
                bar="back",
            ),
            RotationAction(
                time_seconds=4.0,
                sequence=0,
                kind=RotationActionKind.WAIT,
            ),
        ),
        assumptions=("short deterministic healer control",),
    )


def test_healer_kernel_replays_same_input_identically() -> None:
    service = _service()

    first = service.simulate(build_snapshot=_snapshot(), plan=_healer_plan())
    second = service.simulate(build_snapshot=_snapshot(), plan=_healer_plan())

    assert first == second
    assert first.deterministic_signature == second.deterministic_signature
    assert first.final_bar == "back"
    assert [event.source for event in first.events] == [
        "Combat Prayer",
        "light_attack",
        "bar_swap",
        "Illustrious Healing",
        "wait",
    ]


def test_healer_kernel_preserves_same_timestamp_rotation_sequence() -> None:
    result = _service().simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
    )

    at_two = [event for event in result.events if event.time_seconds == 2.0]

    assert [(event.sequence, event.source) for event in at_two] == [
        (0, "bar_swap"),
        (1, "Illustrious Healing"),
    ]
    assert result.final_bar == "back"


def test_healer_kernel_reports_unwired_consequences_instead_of_zeroing_them() -> None:
    result = _service().simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
    )

    assert any(
        "Combat Prayer" in message and "non-healing skill consequences" in message
        for message in result.unresolved
    )
    assert any(
        "Illustrious Healing" in message and "non-healing skill consequences" in message
        for message in result.unresolved
    )
    assert not any("wait consequence" in message for message in result.unresolved)
    assert not any("bar_swap consequence" in message for message in result.unresolved)


def test_kernel_fails_closed_when_rotation_identity_does_not_match_build() -> None:
    bad_plan = RotationPlan(
        character_name="Somebody Else",
        build_name="DF Healer",
        duration_seconds=1.0,
        actions=(),
    )

    try:
        _service().simulate(
            build_snapshot=_snapshot(),
            plan=bad_plan,
        )
    except ValueError as exc:
        assert "rotation character" in str(exc)
    else:
        raise AssertionError("Expected mismatched rotation/build identity to fail closed")


def test_kernel_surfaces_existing_phase13_bar_legality_violation() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=2.0,
        actions=(
            RotationAction(
                time_seconds=1.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="back",
            ),
        ),
    )

    result = _service().simulate(
        build_snapshot=_snapshot(),
        plan=plan,
        initial_bar="front",
    )

    assert result.final_bar == "front"
    assert any("scheduled bar does not match the active bar" in value for value in result.unresolved)
