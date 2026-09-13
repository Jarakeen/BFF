from types import SimpleNamespace

from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_target_health_aware_skill_damage_service import (
    RotationCandidateTargetHealthAwareSkillDamageService,
)


class _Base:
    def __init__(self):
        self.calls = 0

    def evaluate_action(self, *, candidate, action):
        self.calls += 1
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=100.0,
        )


class _Bridge:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def evaluate_if_supported(self, *, candidate, action):
        self.calls += 1
        return self.result


def _action():
    return SimpleNamespace(time_seconds=2.0, sequence=0)


def test_reviewed_periodic_target_health_result_wins_without_calling_base() -> None:
    base = _Base()
    reviewed = RotationActionDamageEvidence(
        time_seconds=2.0,
        sequence=0,
        damage_value=250.0,
    )
    bridge = _Bridge(reviewed)
    service = RotationCandidateTargetHealthAwareSkillDamageService(
        base=base,
        periodic_target_health_bridge=bridge,
    )

    result = service.evaluate_action(candidate=SimpleNamespace(), action=_action())

    assert result is reviewed
    assert bridge.calls == 1
    assert base.calls == 0


def test_unhandled_action_delegates_unchanged_to_canonical_base() -> None:
    base = _Base()
    bridge = _Bridge(None)
    service = RotationCandidateTargetHealthAwareSkillDamageService(
        base=base,
        periodic_target_health_bridge=bridge,
    )

    result = service.evaluate_action(candidate=SimpleNamespace(), action=_action())

    assert result.damage_value == 100.0
    assert bridge.calls == 1
    assert base.calls == 1
