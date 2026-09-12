import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_periodic_damage_runtime_projection_service import (
    PeriodicDamageActivationAnchor,
)
from services.rotation_runtime_activation_anchor_evidence_service import (
    RotationRuntimeActivationAnchorEvidence,
    RotationRuntimeActivationAnchorEvidenceService,
)


def _stampede_action(*, time_seconds: float = 4.0, sequence: int = 3):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=sequence,
        kind=RotationActionKind.SKILL,
        name="Stampede",
        bar="back",
    )


def _plan(action: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Runtime Test",
        build_name="DD",
        duration_seconds=20.0,
        actions=(action,),
    )


def test_runtime_anchor_evidence_resolves_exact_semantic_final_plan_action() -> None:
    action = _stampede_action()
    evidence = RotationRuntimeActivationAnchorEvidence(
        skill_entity_id="Stampede",
        action_time_seconds=4.0,
        action_sequence=3,
        activation_anchor=PeriodicDamageActivationAnchor.IMPACT,
        anchor_time_seconds=4.173,
        source="authoritative runtime impact event",
    )
    service = RotationRuntimeActivationAnchorEvidenceService()

    resolver = service.resolver_factory((evidence,))(_plan(action))

    assert evidence.skill_entity_id == "stampede"
    assert resolver(action, PeriodicDamageActivationAnchor.IMPACT) == 4.173
    assert resolver(action, PeriodicDamageActivationAnchor.CAST) is None


def test_runtime_anchor_evidence_fails_closed_when_final_plan_action_moved() -> None:
    evidence = RotationRuntimeActivationAnchorEvidence(
        skill_entity_id="stampede",
        action_time_seconds=4.0,
        action_sequence=3,
        activation_anchor="impact",
        anchor_time_seconds=4.173,
        source="authoritative runtime impact event",
    )
    moved = _stampede_action(time_seconds=5.0, sequence=3)
    resolver = RotationRuntimeActivationAnchorEvidenceService().resolver_factory(
        (evidence,)
    )(_plan(moved))

    assert resolver(moved, PeriodicDamageActivationAnchor.IMPACT) is None


def test_runtime_anchor_evidence_fails_closed_on_semantic_skill_mismatch() -> None:
    evidence = RotationRuntimeActivationAnchorEvidence(
        skill_entity_id="stampede",
        action_time_seconds=4.0,
        action_sequence=3,
        activation_anchor="impact",
        anchor_time_seconds=4.173,
        source="authoritative runtime impact event",
    )
    other = RotationAction(
        time_seconds=4.0,
        sequence=3,
        kind=RotationActionKind.SKILL,
        name="Carve",
        bar="back",
    )
    resolver = RotationRuntimeActivationAnchorEvidenceService().resolver_factory(
        (evidence,)
    )(_plan(other))

    assert resolver(other, PeriodicDamageActivationAnchor.IMPACT) is None


def test_runtime_anchor_evidence_rejects_conflicting_exact_action_anchor() -> None:
    rows = (
        RotationRuntimeActivationAnchorEvidence(
            skill_entity_id="stampede",
            action_time_seconds=4.0,
            action_sequence=3,
            activation_anchor="impact",
            anchor_time_seconds=4.173,
            source="runtime event A",
        ),
        RotationRuntimeActivationAnchorEvidence(
            skill_entity_id="stampede",
            action_time_seconds=4.0,
            action_sequence=3,
            activation_anchor="impact",
            anchor_time_seconds=4.225,
            source="runtime event B",
        ),
    )

    with pytest.raises(ValueError, match="conflicting runtime activation-anchor evidence"):
        RotationRuntimeActivationAnchorEvidenceService().resolver_factory(rows)


def test_runtime_anchor_evidence_rejects_anchor_before_action() -> None:
    with pytest.raises(ValueError, match="cannot precede"):
        RotationRuntimeActivationAnchorEvidence(
            skill_entity_id="stampede",
            action_time_seconds=4.0,
            action_sequence=3,
            activation_anchor="impact",
            anchor_time_seconds=3.9,
            source="invalid runtime event",
        )
