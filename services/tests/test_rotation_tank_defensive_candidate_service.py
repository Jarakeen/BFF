from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_defensive_candidate_service import (
    RotationTankDefensiveActionClaim,
    RotationTankDefensiveCandidateService,
)
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
)


def _candidate(*actions: RotationAction) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Tank",
            build_name="Main Tank",
            duration_seconds=30.0,
            actions=tuple(actions),
            assumptions=("seed",),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _obligation(
    obligation_id: str = "heavy_01",
    *,
    start: float = 10.0,
    end: float = 10.8,
    allowed=(RotationActionKind.BLOCK,),
    minimum: int = 1,
    bar: str | None = "front",
) -> RotationTankDefensiveObligation:
    return RotationTankDefensiveObligation(
        obligation_id=obligation_id,
        window_start_seconds=start,
        window_end_seconds=end,
        allowed_actions=allowed,
        minimum_responses=minimum,
        bar=bar,
    )


def test_preserves_candidate_when_existing_response_already_satisfies_obligation() -> None:
    candidate = _candidate(
        RotationAction(10.4, 0, RotationActionKind.BLOCK, bar="front")
    )

    projection = RotationTankDefensiveCandidateService().project(
        candidate=candidate,
        obligations=(_obligation(),),
    )

    assert projection.resolved is True
    assert projection.inserted_claims == ()
    assert projection.preserved_obligation_ids == ("heavy_01",)
    assert projection.candidate is not None
    assert projection.candidate.plan.actions == candidate.plan.actions


def test_inserts_exact_claim_when_required_response_is_missing() -> None:
    candidate = _candidate(
        RotationAction(9.0, 0, RotationActionKind.SKILL, name="Pierce Armor", bar="front")
    )
    claim = RotationTankDefensiveActionClaim(
        obligation_id="heavy_01",
        action_kind=RotationActionKind.BLOCK,
        action_time_seconds=10.4,
        action_sequence=0,
        bar="front",
        provenance=("reviewed tank timing policy",),
    )

    projection = RotationTankDefensiveCandidateService().project(
        candidate=candidate,
        obligations=(_obligation(),),
        claims=(claim,),
    )

    assert projection.resolved is True
    assert projection.inserted_claims == (claim,)
    assert projection.candidate is not None
    assert any(
        action.kind is RotationActionKind.BLOCK and action.time_seconds == 10.4
        for action in projection.candidate.plan.actions
    )
    assert projection.candidate.candidate_id == candidate.candidate_id
    assert projection.candidate.refresh_leads == candidate.refresh_leads
    assert projection.candidate.action_claims == candidate.action_claims


def test_claim_never_displaces_an_occupied_rotation_slot() -> None:
    candidate = _candidate(
        RotationAction(10.4, 0, RotationActionKind.SKILL, name="Pierce Armor", bar="front")
    )
    claim = RotationTankDefensiveActionClaim(
        obligation_id="heavy_01",
        action_kind=RotationActionKind.BLOCK,
        action_time_seconds=10.4,
        action_sequence=0,
        bar="front",
    )

    projection = RotationTankDefensiveCandidateService().project(
        candidate=candidate,
        obligations=(_obligation(),),
        claims=(claim,),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "heavy_01: defensive claim slot 10.4s sequence 0 is occupied by skill",
    )


def test_claim_must_use_allowed_response_inside_exact_obligation_window() -> None:
    service = RotationTankDefensiveCandidateService()
    candidate = _candidate()
    obligation = _obligation(allowed=(RotationActionKind.BLOCK,))

    wrong_kind = service.project(
        candidate=candidate,
        obligations=(obligation,),
        claims=(
            RotationTankDefensiveActionClaim(
                obligation_id="heavy_01",
                action_kind=RotationActionKind.DODGE,
                action_time_seconds=10.4,
                action_sequence=0,
            ),
        ),
    )
    outside_window = service.project(
        candidate=candidate,
        obligations=(obligation,),
        claims=(
            RotationTankDefensiveActionClaim(
                obligation_id="heavy_01",
                action_kind=RotationActionKind.BLOCK,
                action_time_seconds=11.0,
                action_sequence=0,
            ),
        ),
    )

    assert wrong_kind.candidate is None
    assert "not an allowed defensive response" in wrong_kind.unresolved[0]
    assert outside_window.candidate is None
    assert "falls outside" in outside_window.unresolved[0]


def test_repeated_mechanics_require_each_occurrence_to_be_satisfied() -> None:
    candidate = _candidate()
    first = _obligation("heavy_01", start=10.0, end=10.5)
    second = _obligation("heavy_02", start=20.0, end=20.5)
    first_claim = RotationTankDefensiveActionClaim(
        obligation_id="heavy_01",
        action_kind=RotationActionKind.BLOCK,
        action_time_seconds=10.2,
        action_sequence=0,
        bar="front",
    )

    projection = RotationTankDefensiveCandidateService().project(
        candidate=candidate,
        obligations=(first, second),
        claims=(first_claim,),
    )

    assert projection.candidate is None
    assert projection.inserted_claims == (first_claim,)
    assert projection.unresolved == (
        "heavy_02: scheduled 0 of 1 required defensive responses",
    )


def test_multiple_claims_can_satisfy_one_minimum_response_obligation() -> None:
    candidate = _candidate()
    obligation = _obligation(minimum=2, start=10.0, end=12.0)
    claims = (
        RotationTankDefensiveActionClaim(
            obligation_id="heavy_01",
            action_kind=RotationActionKind.BLOCK,
            action_time_seconds=10.2,
            action_sequence=0,
            bar="front",
        ),
        RotationTankDefensiveActionClaim(
            obligation_id="heavy_01",
            action_kind=RotationActionKind.BLOCK,
            action_time_seconds=11.2,
            action_sequence=0,
            bar="front",
        ),
    )

    projection = RotationTankDefensiveCandidateService().project(
        candidate=candidate,
        obligations=(obligation,),
        claims=claims,
    )

    assert projection.resolved is True
    assert projection.inserted_claims == claims
    assert projection.candidate is not None


def test_unknown_obligation_claim_fails_closed() -> None:
    projection = RotationTankDefensiveCandidateService().project(
        candidate=_candidate(),
        obligations=(_obligation(),),
        claims=(
            RotationTankDefensiveActionClaim(
                obligation_id="unknown",
                action_kind=RotationActionKind.BLOCK,
                action_time_seconds=10.2,
                action_sequence=0,
            ),
        ),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "unknown: defensive action claim references unknown obligation",
    )


def test_claim_bar_must_not_contradict_obligation_bar() -> None:
    projection = RotationTankDefensiveCandidateService().project(
        candidate=_candidate(),
        obligations=(_obligation(bar="front"),),
        claims=(
            RotationTankDefensiveActionClaim(
                obligation_id="heavy_01",
                action_kind=RotationActionKind.BLOCK,
                action_time_seconds=10.2,
                action_sequence=0,
                bar="back",
            ),
        ),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "heavy_01: defensive claim bar back does not match required front bar",
    )
