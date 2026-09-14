from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_tank_encounter_priority_context_service import RotationTankEncounterPriorityCue
from services.rotation_tank_priority_candidate_assessment_service import (
    RotationTankPriorityCandidateAssessmentService,
    RotationTankPriorityCueStatus,
)


def _cue(priority: int, target: str, actor: str | None, directive: str):
    return RotationTankEncounterPriorityCue(
        encounter_id="xalvakka",
        lane_id="add_handler",
        member_id="tank-b",
        priority=priority,
        responsibility_id=f"r{priority}",
        target_key=target,
        actor_name=actor,
        directive=directive,
        trigger="reviewed_add_activity",
        hard_policy=False,
        interpretation="fixture",
    )


def _plan(*targets: str) -> RotationPlan:
    return RotationPlan(
        character_name="Tank",
        build_name="Fixture",
        duration_seconds=20.0,
        actions=tuple(
            RotationAction(
                time_seconds=float(index + 1),
                sequence=index,
                kind=RotationActionKind.SKILL,
                name="taunt",
                bar="front",
                target_key=target,
            )
            for index, target in enumerate(targets)
        ),
    )


def test_assessment_uses_explicit_targets_and_priority_order() -> None:
    context = (
        _cue(20, "encounter_adds", "Iron Atronach", "maintain_iron"),
        _cue(40, "encounter_adds", "Daedroth", "contextual_daedroth"),
    )
    service = RotationTankPriorityCandidateAssessmentService()

    iron_only = service.assess(
        candidate_id="iron-only",
        plan=_plan("iron_atronach"),
        priority_context=context,
    )
    daedroth_only = service.assess(
        candidate_id="daedroth-only",
        plan=_plan("daedroth"),
        priority_context=context,
    )

    assert iron_only.cues[0].status is RotationTankPriorityCueStatus.SATISFIED
    assert iron_only.cues[1].status is RotationTankPriorityCueStatus.UNSATISFIED
    assert daedroth_only.cues[0].status is RotationTankPriorityCueStatus.UNSATISFIED
    assert daedroth_only.cues[1].status is RotationTankPriorityCueStatus.SATISFIED
    assert iron_only.preference_key < daedroth_only.preference_key


def test_missing_target_identity_is_unresolved_not_guessed() -> None:
    assessment = RotationTankPriorityCandidateAssessmentService().assess(
        candidate_id="opaque",
        plan=_plan(),
        priority_context=(
            _cue(20, "encounter_adds", "Iron Atronach", "maintain_iron"),
        ),
    )

    assert assessment.cues[0].status is RotationTankPriorityCueStatus.UNRESOLVED
    assert "no explicit target identities" in assessment.cues[0].reason
