from __future__ import annotations

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.combat_simulation_outgoing_damage_service import (
    CombatSimulationOutgoingDamageService,
)
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


class _DamageProvider:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def evaluate_action(self, *, candidate, action):
        self.calls.append((candidate, action))
        value = self.values[(action.time_seconds, action.sequence)]
        if isinstance(value, tuple):
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=None,
                unresolved=value,
            )
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=float(value),
        )


def _plan():
    return RotationPlan(
        character_name="Damage Tester",
        build_name="DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(
                0.0,
                1,
                RotationActionKind.SKILL,
                name="Force Pulse",
                bar="front",
            ),
            RotationAction(1.0, 0, RotationActionKind.WAIT),
        ),
    )


def test_bridge_projects_resolved_rotation_damage_to_explicit_target() -> None:
    provider = _DamageProvider({(0.0, 0): 3000.0, (0.0, 1): 7000.0})
    result = CombatSimulationOutgoingDamageService(
        action_damage_evidence_provider=provider,
    ).project(
        plan=_plan(),
        target_identity="Boss",
    )

    assert result.unresolved == ()
    assert result.resolved_action_keys == ((0.0, 0), (0.0, 1))
    assert [
        (item.source, item.recipient, item.amount)
        for item in result.damage
    ] == [
        ("light_attack", "Boss", 3000.0),
        ("Force Pulse", "Boss", 7000.0),
    ]
    assert len(provider.calls) == 2


def test_bridge_preserves_provider_unresolved_and_does_not_invent_damage() -> None:
    provider = _DamageProvider({
        (0.0, 0): ("light attack target state unavailable",),
        (0.0, 1): 7000.0,
    })
    result = CombatSimulationOutgoingDamageService(
        action_damage_evidence_provider=provider,
    ).project(
        plan=_plan(),
        target_identity="Boss",
    )

    assert len(result.damage) == 1
    assert result.damage[0].source == "Force Pulse"
    assert result.resolved_action_keys == ((0.0, 1),)
    assert result.unresolved == (
        "0s #0 light_attack: light attack target state unavailable",
    )


def test_bridge_accepts_exact_existing_generated_candidate() -> None:
    plan = _plan()
    candidate = GeneratedRotationCandidate(
        candidate_id="real-candidate",
        plan=plan,
        refresh_leads=(),
        action_claims=(),
    )
    provider = _DamageProvider({(0.0, 0): 3000.0, (0.0, 1): 7000.0})

    CombatSimulationOutgoingDamageService(
        action_damage_evidence_provider=provider,
    ).project(
        plan=plan,
        target_identity="Boss",
        candidate=candidate,
    )

    assert all(call[0] is candidate for call in provider.calls)


def test_bridge_rejects_candidate_for_different_plan() -> None:
    provider = _DamageProvider({(0.0, 0): 3000.0, (0.0, 1): 7000.0})
    other = GeneratedRotationCandidate(
        candidate_id="other",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="DD",
            duration_seconds=1.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )

    try:
        CombatSimulationOutgoingDamageService(
            action_damage_evidence_provider=provider,
        ).project(
            plan=_plan(),
            target_identity="Boss",
            candidate=other,
        )
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("Expected mismatched candidate plan to fail closed")



def test_bridge_marks_zero_damage_resolved_without_emitting_damage() -> None:
    plan = RotationPlan(
        character_name="Damage Tester",
        build_name="DD",
        duration_seconds=2.0,
        actions=(
            RotationAction(
                1.0,
                0,
                RotationActionKind.SKILL,
                name="Resolved Non-Damage Activation",
                bar="front",
            ),
        ),
    )
    provider = _DamageProvider({(1.0, 0): 0.0})

    result = CombatSimulationOutgoingDamageService(
        action_damage_evidence_provider=provider,
    ).project(plan=plan, target_identity="Boss")

    assert result.damage == ()
    assert result.resolved_action_keys == ((1.0, 0),)
    assert result.unresolved == ()
