from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from models.effective_build_snapshot import EffectiveBuildSnapshot
from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationIncomingDamage,
    CombatSimulationOutgoingDamage,
    CombatSimulationResourceResult,
    CombatSimulationTargetState,
)
from services.combat_simulation_healing_service import CombatSimulationHealingProjection
from services.combat_simulation_outgoing_damage_service import (
    CombatSimulationOutgoingDamageProjection,
)
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
        "Combat Prayer" in message and "remaining skill consequences" in message
        for message in result.unresolved
    )
    assert any(
        "Illustrious Healing" in message and "remaining skill consequences" in message
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



def test_kernel_routes_outgoing_damage_into_enemy_health_state() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )

    result = _service().simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
        target_state=state,
        outgoing_damage=(
            CombatSimulationOutgoingDamage(
                time_seconds=3.0,
                sequence=0,
                source="Resolved Damage",
                recipient="Boss",
                amount=2500.0,
                damage_type="magic",
            ),
        ),
    )

    outgoing = [
        event
        for event in result.events
        if event.event_type == "outgoing_damage"
    ]
    health = [
        event
        for event in result.events
        if event.event_type == "health_change"
        and event.payload_dict().get("recipient") == "Boss"
    ]

    assert len(outgoing) == 1
    assert len(health) == 1
    assert outgoing[0].payload_dict()["amount"] == 2500.0
    assert health[0].payload_dict()["before"] == 10000
    assert health[0].payload_dict()["after"] == 7500
    assert health[0].payload_dict()["origin_event_type"] == "outgoing_damage"



class _StaticOutgoingDamageService:
    def project(self, *, plan, target_identity, candidate=None):
        assert plan is not None
        assert target_identity == "Boss"
        return CombatSimulationOutgoingDamageProjection(
            damage=(
                CombatSimulationOutgoingDamage(
                    time_seconds=1.0,
                    sequence=0,
                    source="light_attack",
                    recipient=target_identity,
                    amount=3000.0,
                    damage_type="magic",
                ),
                CombatSimulationOutgoingDamage(
                    time_seconds=2.0,
                    sequence=1,
                    source="Illustrious Healing",
                    recipient=target_identity,
                    amount=2000.0,
                    damage_type="magic",
                ),
            ),
            resolved_action_keys=((1.0, 0), (2.0, 1)),
            unresolved=(),
        )


def test_kernel_consumes_canonical_action_damage_projection() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )
    service = CombatSimulationService(
        resource_service=_NoopResourceService(),
        healing_service=_NoopHealingService(),
        skill_effect_service=_NoopSkillEffectService(),
        outgoing_damage_service=_StaticOutgoingDamageService(),
    )

    result = service.simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
        target_state=state,
        damage_target_identity="Boss",
    )

    outgoing = [
        event for event in result.events
        if event.event_type == "outgoing_damage"
    ]
    health = [
        event for event in result.events
        if event.event_type == "health_change"
        and event.payload_dict().get("recipient") == "Boss"
    ]

    assert [event.payload_dict()["amount"] for event in outgoing] == [3000.0, 2000.0]
    assert [event.payload_dict()["after"] for event in health] == [7000, 5000]
    assert not any(
        "light_attack consequence projection not yet wired" in message
        for message in result.unresolved
    )
    assert any(
        "Illustrious Healing" in message
        and "damage consequence is wired" in message
        for message in result.unresolved
    )


def test_kernel_fails_closed_when_damage_bridge_has_no_explicit_target() -> None:
    service = CombatSimulationService(
        resource_service=_NoopResourceService(),
        healing_service=_NoopHealingService(),
        skill_effect_service=_NoopSkillEffectService(),
        outgoing_damage_service=_StaticOutgoingDamageService(),
    )

    result = service.simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
    )

    assert any(
        "outgoing damage projection requires explicit target identity" in message
        for message in result.unresolved
    )



def test_kernel_orders_damage_before_health_change_before_death() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=2000,
                maximum_health=10000,
            ),
        ),
    )

    result = _service().simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
        target_state=state,
        outgoing_damage=(
            CombatSimulationOutgoingDamage(
                time_seconds=3.0,
                sequence=0,
                source="Killing Hit",
                recipient="Boss",
                amount=3000.0,
            ),
        ),
    )

    at_three = [
        event
        for event in result.events
        if event.time_seconds == 3.0
        and event.source == "Killing Hit"
    ]

    assert [event.event_type for event in at_three] == [
        "outgoing_damage",
        "health_change",
        "death",
    ]
    assert [event.priority for event in at_three] == [
        30,
        35,
        80,
    ]



def test_kernel_preserves_raw_components_but_coalesces_health_transition() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )

    result = _service().simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
        target_state=state,
        outgoing_damage=(
            CombatSimulationOutgoingDamage(
                time_seconds=3.0,
                sequence=0,
                source="Mixed Skill",
                recipient="Boss",
                amount=2000.0,
                damage_type="magic",
            ),
            CombatSimulationOutgoingDamage(
                time_seconds=3.0,
                sequence=0,
                source="Mixed Skill",
                recipient="Boss",
                amount=3000.0,
                damage_type="flame",
            ),
        ),
    )

    raw = [
        event
        for event in result.events
        if event.event_type == "outgoing_damage"
        and event.source == "Mixed Skill"
    ]
    health = [
        event
        for event in result.events
        if event.event_type == "health_change"
        and event.source == "Mixed Skill"
    ]

    assert [event.payload_dict()["amount"] for event in raw] == [
        2000.0,
        3000.0,
    ]
    assert len(health) == 1
    payload = health[0].payload_dict()
    assert payload["attempted_damage"] == 5000.0
    assert payload["before"] == 10000
    assert payload["after"] == 5000



def test_kernel_separates_damage_and_non_damage_unresolved_evidence() -> None:
    unresolved = _service().simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
    )
    assert any(
        "light_attack consequence projection not yet wired" in message
        for message in unresolved.damage_unresolved
    )

    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )
    resolved = CombatSimulationService(
        resource_service=_NoopResourceService(),
        healing_service=_NoopHealingService(),
        skill_effect_service=_NoopSkillEffectService(),
        outgoing_damage_service=_StaticOutgoingDamageService(),
    ).simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
        target_state=state,
        damage_target_identity="Boss",
    )

    assert not any(
        "light_attack consequence projection not yet wired" in message
        for message in resolved.damage_unresolved
    )
    assert any(
        "Illustrious Healing" in message
        and "unsupported non-damage" in message
        for message in resolved.unresolved
    )
    assert not any(
        "unsupported non-damage" in message
        for message in resolved.damage_unresolved
    )


def test_kernel_marks_unapplied_outgoing_damage_incomplete_without_target_state() -> None:
    result = _service().simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
        outgoing_damage=(
            CombatSimulationOutgoingDamage(
                time_seconds=3.0,
                sequence=0,
                source="Resolved Damage",
                recipient="Boss",
                amount=2500.0,
                damage_type="magic",
            ),
        ),
    )

    assert any(
        "target Health state is required to prove applied damage" in message
        for message in result.damage_unresolved
    )


def test_kernel_marks_same_instant_cross_source_outgoing_collision_damage_unresolved() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        ),
    )

    result = _service().simulate(
        build_snapshot=_snapshot(),
        plan=_healer_plan(),
        target_state=state,
        outgoing_damage=(
            CombatSimulationOutgoingDamage(
                time_seconds=3.0,
                sequence=0,
                source="Skill A",
                recipient="Boss",
                amount=2000.0,
            ),
            CombatSimulationOutgoingDamage(
                time_seconds=3.0,
                sequence=0,
                source="Skill B",
                recipient="Boss",
                amount=3000.0,
            ),
        ),
    )

    assert any(
        "Health consequence ordering is unresolved" in message
        for message in result.damage_unresolved
    )
    assert not any(
        event.event_type == "health_change"
        and event.payload_dict().get("recipient") == "Boss"
        for event in result.events
    )


def test_injected_damage_rejects_non_finite_time() -> None:
    for cls, label, recipient in (
        (CombatSimulationIncomingDamage, "incoming", "Magrat"),
        (CombatSimulationOutgoingDamage, "outgoing", "Boss"),
    ):
        for value in (float("nan"), float("inf"), float("-inf")):
            try:
                cls(
                    time_seconds=value,
                    sequence=0,
                    source="Invalid Fixture",
                    recipient=recipient,
                    amount=1000.0,
                )
            except ValueError as exc:
                assert "finite and non-negative" in str(exc)
            else:
                raise AssertionError(
                    f"Expected non-finite {label} damage time to fail closed"
                )


def test_injected_damage_rejects_non_finite_amount() -> None:
    for cls, label, recipient in (
        (CombatSimulationIncomingDamage, "incoming", "Magrat"),
        (CombatSimulationOutgoingDamage, "outgoing", "Boss"),
    ):
        for value in (float("nan"), float("inf"), float("-inf")):
            try:
                cls(
                    time_seconds=1.0,
                    sequence=0,
                    source="Invalid Fixture",
                    recipient=recipient,
                    amount=value,
                )
            except ValueError as exc:
                assert "finite and non-negative" in str(exc)
            else:
                raise AssertionError(
                    f"Expected non-finite {label} damage amount to fail closed"
                )
