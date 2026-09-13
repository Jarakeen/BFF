from __future__ import annotations

from minmax.combat_state_snapshot import CombatStateSnapshot, CombatantSnapshot
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequenceType,
)
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidence,
    RotationExecuteComponentEvidence,
)
from services.rotation_execute_runtime_state_service import (
    RotationExecuteRuntimeStateService,
    RotationExecuteRuntimeStatus,
)


def _component(*, threshold: float = 0.25) -> RotationExecuteComponentEvidence:
    return RotationExecuteComponentEvidence(
        skill_name="Executioner",
        entity_id="executioner",
        skill_rank_id=123,
        coefficient_number=1,
        threshold=threshold,
        consequence_type=SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
        maximum_bonus_fraction=4.0,
        condition_evidence="below 25% Health",
        consequence_evidence="up to 400% more damage",
    )


def _candidate(*components: RotationExecuteComponentEvidence) -> RotationExecuteCandidateEvidence:
    return RotationExecuteCandidateEvidence(
        requested_skill_name="Executioner",
        resolved_skill_name="Executioner",
        entity_id="executioner",
        components=components,
    )


def _snapshot(*, current_health: float | None, maximum_health: float | None = 100.0):
    return CombatStateSnapshot(
        time_seconds=12.0,
        player=CombatantSnapshot("player", current_health=100.0, maximum_health=100.0),
        targets=(
            CombatantSnapshot(
                "boss",
                current_health=current_health,
                maximum_health=maximum_health,
            ),
        ),
    )


def test_threshold_execute_is_active_below_reviewed_health_fraction() -> None:
    result = RotationExecuteRuntimeStateService().resolve(
        candidate=_candidate(_component()),
        snapshot=_snapshot(current_health=24.0),
        target_identity="boss",
    )

    assert result.status is RotationExecuteRuntimeStatus.ACTIVE
    assert result.active
    assert result.active_components == (_component(),)
    assert result.unresolved == ()


def test_threshold_execute_is_inactive_at_or_above_reviewed_threshold() -> None:
    result = RotationExecuteRuntimeStateService().resolve(
        candidate=_candidate(_component()),
        snapshot=_snapshot(current_health=25.0),
        target_identity="boss",
    )

    assert result.status is RotationExecuteRuntimeStatus.INACTIVE
    assert not result.active
    assert result.active_components == ()
    assert result.unresolved == ()


def test_missing_target_health_fails_closed_as_unknown() -> None:
    result = RotationExecuteRuntimeStateService().resolve(
        candidate=_candidate(_component()),
        snapshot=_snapshot(current_health=None),
        target_identity="boss",
    )

    assert result.status is RotationExecuteRuntimeStatus.UNKNOWN
    assert result.unresolved == ("execute runtime target 'boss' Health is unknown",)


def test_missing_target_identity_fails_closed_as_unknown() -> None:
    result = RotationExecuteRuntimeStateService().resolve(
        candidate=_candidate(_component()),
        snapshot=_snapshot(current_health=20.0),
        target_identity="missing",
    )

    assert result.status is RotationExecuteRuntimeStatus.UNKNOWN
    assert result.unresolved == ("execute runtime target 'missing' is absent from snapshot",)


def test_candidate_without_positive_execute_evidence_is_unknown_not_inactive() -> None:
    result = RotationExecuteRuntimeStateService().resolve(
        candidate=_candidate(),
        snapshot=_snapshot(current_health=20.0),
        target_identity="boss",
    )

    assert result.status is RotationExecuteRuntimeStatus.UNKNOWN
    assert result.unresolved == (
        "no canonical target-health threshold execute evidence for 'Executioner'",
    )


def test_any_active_reviewed_threshold_component_makes_candidate_active() -> None:
    result = RotationExecuteRuntimeStateService().resolve(
        candidate=_candidate(_component(threshold=0.20), _component(threshold=0.30)),
        snapshot=_snapshot(current_health=25.0),
        target_identity="boss",
    )

    assert result.status is RotationExecuteRuntimeStatus.ACTIVE
    assert tuple(item.threshold for item in result.active_components) == (0.30,)
