from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_defensive_candidate_service import (
    RotationTankDefensiveActionClaim,
)
from services.rotation_tank_defensive_family_projector_service import (
    RotationTankDefensiveFamilyProjectorService,
)
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
)


def _obligation() -> RotationTankDefensiveObligation:
    return RotationTankDefensiveObligation(
        obligation_id="boss:heavy:01",
        window_start_seconds=10.0,
        window_end_seconds=11.0,
        allowed_actions=(RotationActionKind.BLOCK,),
        minimum_responses=1,
        bar="front",
    )


def _claim(**overrides) -> RotationTankDefensiveActionClaim:
    values = {
        "obligation_id": "boss:heavy:01",
        "action_kind": RotationActionKind.BLOCK,
        "action_time_seconds": 10.5,
        "action_sequence": 0,
        "bar": "front",
    }
    values.update(overrides)
    return RotationTankDefensiveActionClaim(**values)


def _candidate(candidate_id="candidate", *, actions=()) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tank",
            build_name="Main Tank",
            duration_seconds=20.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
    )


def test_family_projector_inserts_missing_exact_defensive_claim() -> None:
    projector = RotationTankDefensiveFamilyProjectorService(
        obligations=(_obligation(),),
        claims=(_claim(),),
    )

    projected = projector(_candidate())

    assert projected.candidate_id == "candidate"
    assert projected.plan.unresolved == ()
    assert any(
        action.kind is RotationActionKind.BLOCK
        and action.time_seconds == 10.5
        and action.sequence == 0
        and action.bar == "front"
        for action in projected.plan.actions
    )


def test_already_satisfied_candidate_ignores_unnecessary_shared_claim_collision() -> None:
    existing = (
        RotationAction(
            time_seconds=10.2,
            sequence=0,
            kind=RotationActionKind.BLOCK,
            bar="front",
        ),
        RotationAction(
            time_seconds=10.5,
            sequence=0,
            kind=RotationActionKind.SKILL,
            name="Pierce Armor",
            bar="front",
        ),
    )
    projector = RotationTankDefensiveFamilyProjectorService(
        obligations=(_obligation(),),
        claims=(_claim(),),
    )

    projected = projector(_candidate(actions=existing))

    assert projected.plan.unresolved == ()
    assert projected.plan.actions == existing


def test_candidate_specific_claim_collision_becomes_plan_unresolved_not_family_abort() -> None:
    occupied = (
        RotationAction(
            time_seconds=10.5,
            sequence=0,
            kind=RotationActionKind.SKILL,
            name="Pierce Armor",
            bar="front",
        ),
    )
    projector = RotationTankDefensiveFamilyProjectorService(
        obligations=(_obligation(),),
        claims=(_claim(),),
    )

    projected = projector(_candidate(actions=occupied))

    assert projected.candidate_id == "candidate"
    assert projected.plan.actions == occupied
    assert projected.plan.unresolved == (
        "boss:heavy:01: defensive claim slot 10.5s sequence 0 is occupied by skill",
    )


def test_missing_claim_for_unsatisfied_obligation_stays_candidate_specific_unresolved() -> None:
    projector = RotationTankDefensiveFamilyProjectorService(
        obligations=(_obligation(),),
        claims=(),
    )

    projected = projector(_candidate())

    assert projected.plan.unresolved == (
        "boss:heavy:01: scheduled 0 of 1 required defensive responses",
    )
