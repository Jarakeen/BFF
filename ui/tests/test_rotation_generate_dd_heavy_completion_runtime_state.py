from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
import ui.rotation_generate_dd_role_evidence_support as dd_support


def test_generate_heavy_uses_completion_time_for_attacker_and_target_runtime_state(
    monkeypatch,
) -> None:
    action = RotationAction(
        4.0,
        0,
        RotationActionKind.HEAVY_ATTACK,
        bar="front",
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="heavy-completion-state",
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="Heavy Completion State",
            duration_seconds=10.0,
            actions=(action,),
        ),
        refresh_leads=(),
        action_claims=(),
    )
    completion = SimpleNamespace(
        action_time_seconds=4.0,
        action_sequence=0,
        completion_time_seconds=5.8,
    )
    monkeypatch.setattr(
        dd_support.RotationHeavySustainProjectionService,
        "completion_evidence_from_verified_reservations",
        staticmethod(lambda _plan: (completion,)),
    )

    evaluation_calls = []
    attacker_state = CombatState(active_buffs=("Major Berserk",))

    def evaluate_at(**kwargs):
        evaluation_calls.append(kwargs)
        return object(), SimpleNamespace(combat_state=attacker_state), ()

    monkeypatch.setattr(dd_support, "_weapon_attack_evaluation_at", evaluate_at)

    target_calls = []
    target_state = CombatState(active_buffs=("Major Vulnerability",))

    def target_resolver(time_seconds, sequence=None):
        target_calls.append((float(time_seconds), sequence))
        return target_state

    captured = {}

    class _HeavyDamageService:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def evaluate_action(self, *, candidate, action):
            return RotationActionDamageEvidence(
                time_seconds=action.time_seconds,
                sequence=action.sequence,
                damage_value=123.0,
            )

    monkeypatch.setattr(
        dd_support,
        "RotationCandidateHeavyAttackDamageEvidenceService",
        _HeavyDamageService,
    )

    provider = dd_support._RotationGenerateBarAwareHeavyAttackDamageProvider(
        evaluation=SimpleNamespace(resolved=True, build=object()),
        static_context=object(),
        target_resistance=18200.0,
        runtime_build_context_resolver=lambda *_args, **_kwargs: None,
        runtime_target_combat_state_resolver=target_resolver,
    )

    result = provider.evaluate_action(candidate=candidate, action=action)

    assert result.damage_value == 123.0
    assert len(evaluation_calls) == 1
    assert evaluation_calls[0]["runtime_point"] == (5.8, None)
    assert target_calls == [(5.8, None)]
    assert captured["completion_evidence"] == (completion,)
    assert captured["attacker_combat_state"] is attacker_state
    assert captured["target_combat_state"] is target_state
