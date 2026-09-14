from types import SimpleNamespace

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_candidate_service import (
    RotationTankTauntActionClaim,
    RotationTankTauntCandidateService,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
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


def _requirement(
    requirement_id: str = "taunt_01",
    *,
    start: float = 10.0,
    end: float = 12.0,
    minimum: int = 1,
    bar: str | None = "front",
    target_key: str | None = None,
) -> RotationTankTauntApplicationRequirement:
    return RotationTankTauntApplicationRequirement(
        requirement_id=requirement_id,
        source_skill_name="Pierce Armor",
        window_start_seconds=start,
        window_end_seconds=end,
        minimum_applications=minimum,
        bar=bar,
        target_key=target_key,
    )


def _slot(*bars: str, kind: RotationActionKind = RotationActionKind.SKILL):
    return RotationActionSlotRequirement(
        action_name="Pierce Armor",
        allowed_bars=tuple(bars),
        action_kind=kind,
    )


class _FakeTauntObligationService:
    def assess(self, *, plan, requirement):
        applications = tuple(
            action
            for action in plan.actions
            if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
            and str(action.name or "").casefold()
            == requirement.source_skill_name.casefold()
            and requirement.window_start_seconds <= action.time_seconds <= requirement.window_end_seconds
            and (requirement.bar is None or action.bar == requirement.bar)
            and (
                requirement.target_key is None
                or action.target_key == requirement.target_key
            )
        )
        return SimpleNamespace(
            resolved=True,
            satisfied=len(applications) >= requirement.minimum_applications,
            applications=applications,
            unresolved=(),
        )


def _service() -> RotationTankTauntCandidateService:
    return RotationTankTauntCandidateService(
        "unused.db",
        obligation_service=_FakeTauntObligationService(),
    )


def test_preserves_existing_taunt_application_without_needing_new_slot_proof() -> None:
    candidate = _candidate(
        RotationAction(10.5, 0, RotationActionKind.SKILL, name="Pierce Armor", bar="front")
    )

    projection = _service().project(candidate=candidate, requirements=(_requirement(),))

    assert projection.resolved is True
    assert projection.inserted_claims == ()
    assert projection.preserved_requirement_ids == ("taunt_01",)
    assert projection.candidate is not None
    assert projection.candidate.plan.actions == candidate.plan.actions


def test_inserts_exact_source_skill_claim_when_saved_build_proves_slot() -> None:
    claim = RotationTankTauntActionClaim(
        requirement_id="taunt_01",
        action_time_seconds=10.5,
        action_sequence=0,
        bar="front",
        provenance=("reviewed tank policy",),
    )

    projection = _service().project(
        candidate=_candidate(),
        requirements=(_requirement(),),
        claims=(claim,),
        slot_requirements=(_slot("front"),),
    )

    assert projection.resolved is True
    assert projection.inserted_claims == (claim,)
    assert projection.candidate is not None
    action = projection.candidate.plan.actions[0]
    assert action.kind is RotationActionKind.SKILL
    assert action.name == "Pierce Armor"
    assert action.time_seconds == 10.5
    assert action.bar == "front"


def test_target_specific_requirement_is_inherited_by_inserted_taunt_claim() -> None:
    requirement = _requirement(target_key="reef_guardian_left")
    projection = _service().project(
        candidate=_candidate(),
        requirements=(requirement,),
        claims=(RotationTankTauntActionClaim("taunt_01", 10.5, 0, bar="front"),),
        slot_requirements=(_slot("front"),),
    )

    assert projection.resolved is True
    assert projection.candidate is not None
    assert projection.candidate.plan.actions[0].target_key == "reef_guardian_left"


def test_claim_target_cannot_contradict_required_target_identity() -> None:
    requirement = _requirement(target_key="reef_guardian_left")
    projection = _service().project(
        candidate=_candidate(),
        requirements=(requirement,),
        claims=(
            RotationTankTauntActionClaim(
                "taunt_01",
                10.5,
                0,
                bar="front",
                target_key="reef_guardian_right",
            ),
        ),
        slot_requirements=(_slot("front"),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "taunt_01: taunt claim target reef_guardian_right does not match required target reef_guardian_left",
    )


def test_existing_wrong_target_does_not_preserve_target_specific_requirement() -> None:
    candidate = _candidate(
        RotationAction(
            10.5,
            0,
            RotationActionKind.SKILL,
            name="Pierce Armor",
            bar="front",
            target_key="reef_guardian_right",
        )
    )
    requirement = _requirement(target_key="reef_guardian_left")
    projection = _service().project(
        candidate=candidate,
        requirements=(requirement,),
        claims=(),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "taunt_01: scheduled 0 of 1 required taunt applications",
    )


def test_missing_saved_build_slot_evidence_blocks_new_taunt_cast() -> None:
    projection = _service().project(
        candidate=_candidate(),
        requirements=(_requirement(),),
        claims=(RotationTankTauntActionClaim("taunt_01", 10.5, 0, bar="front"),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "taunt_01: saved-build slot evidence does not prove Pierce Armor is slotted as skill",
    )


def test_claimed_bar_must_be_proven_by_saved_build_slot_evidence() -> None:
    requirement = _requirement(bar=None)
    projection = _service().project(
        candidate=_candidate(),
        requirements=(requirement,),
        claims=(RotationTankTauntActionClaim("taunt_01", 10.5, 0, bar="back"),),
        slot_requirements=(_slot("front"),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "taunt_01: Pierce Armor is not slotted on the claimed back bar",
    )


def test_single_saved_bar_can_resolve_unspecified_claim_bar() -> None:
    requirement = _requirement(bar=None)
    projection = _service().project(
        candidate=_candidate(),
        requirements=(requirement,),
        claims=(RotationTankTauntActionClaim("taunt_01", 10.5, 0),),
        slot_requirements=(_slot("back"),),
    )

    assert projection.resolved is True
    assert projection.candidate is not None
    assert projection.candidate.plan.actions[0].bar == "back"


def test_two_saved_bars_require_explicit_claim_bar() -> None:
    requirement = _requirement(bar=None)
    projection = _service().project(
        candidate=_candidate(),
        requirements=(requirement,),
        claims=(RotationTankTauntActionClaim("taunt_01", 10.5, 0),),
        slot_requirements=(_slot("front", "back"),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "taunt_01: Pierce Armor is slotted on multiple bars and no exact taunt claim bar was supplied",
    )


def test_action_kind_must_match_saved_build_slot_kind() -> None:
    projection = _service().project(
        candidate=_candidate(),
        requirements=(_requirement(),),
        claims=(
            RotationTankTauntActionClaim(
                "taunt_01",
                10.5,
                0,
                action_kind=RotationActionKind.ULTIMATE,
                bar="front",
            ),
        ),
        slot_requirements=(_slot("front", kind=RotationActionKind.SKILL),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "taunt_01: saved-build slot evidence does not prove Pierce Armor is slotted as ultimate",
    )


def test_shared_claim_is_ignored_when_candidate_already_satisfies_requirement() -> None:
    candidate = _candidate(
        RotationAction(10.2, 0, RotationActionKind.SKILL, name="Pierce Armor", bar="front"),
        RotationAction(11.0, 0, RotationActionKind.SKILL, name="Heroic Slash", bar="front"),
    )
    unnecessary_claim = RotationTankTauntActionClaim(
        requirement_id="taunt_01",
        action_time_seconds=11.0,
        action_sequence=0,
        bar="front",
    )

    projection = _service().project(
        candidate=candidate,
        requirements=(_requirement(),),
        claims=(unnecessary_claim,),
    )

    assert projection.resolved is True
    assert projection.inserted_claims == ()
    assert projection.candidate is not None
    assert projection.candidate.plan.actions == candidate.plan.actions


def test_claim_never_displaces_occupied_slot() -> None:
    candidate = _candidate(
        RotationAction(10.5, 0, RotationActionKind.SKILL, name="Heroic Slash", bar="front")
    )
    claim = RotationTankTauntActionClaim(
        requirement_id="taunt_01",
        action_time_seconds=10.5,
        action_sequence=0,
        bar="front",
    )

    projection = _service().project(
        candidate=candidate,
        requirements=(_requirement(),),
        claims=(claim,),
        slot_requirements=(_slot("front"),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "taunt_01: taunt claim slot 10.5s sequence 0 is occupied by skill",
    )


def test_repeated_requirements_each_need_their_own_application() -> None:
    first = _requirement("taunt_01", start=10.0, end=11.0)
    second = _requirement("taunt_02", start=20.0, end=21.0)
    first_claim = RotationTankTauntActionClaim(
        requirement_id="taunt_01",
        action_time_seconds=10.5,
        action_sequence=0,
        bar="front",
    )

    projection = _service().project(
        candidate=_candidate(),
        requirements=(first, second),
        claims=(first_claim,),
        slot_requirements=(_slot("front"),),
    )

    assert projection.candidate is None
    assert projection.inserted_claims == (first_claim,)
    assert projection.unresolved == (
        "taunt_02: scheduled 0 of 1 required taunt applications",
    )


def test_claim_window_bar_and_unknown_requirement_fail_closed() -> None:
    service = _service()
    requirement = _requirement()
    slots = (_slot("front"),)

    outside = service.project(
        candidate=_candidate(),
        requirements=(requirement,),
        claims=(RotationTankTauntActionClaim("taunt_01", 15.0, 0, bar="front"),),
        slot_requirements=slots,
    )
    wrong_bar = service.project(
        candidate=_candidate(),
        requirements=(requirement,),
        claims=(RotationTankTauntActionClaim("taunt_01", 10.5, 0, bar="back"),),
        slot_requirements=slots,
    )
    unknown = service.project(
        candidate=_candidate(),
        requirements=(requirement,),
        claims=(RotationTankTauntActionClaim("unknown", 10.5, 0, bar="front"),),
        slot_requirements=slots,
    )

    assert outside.candidate is None and "falls outside" in outside.unresolved[0]
    assert wrong_bar.candidate is None and "does not match required front bar" in wrong_bar.unresolved[0]
    assert unknown.candidate is None and "references unknown requirement" in unknown.unresolved[0]


def test_multiple_claims_can_satisfy_explicit_minimum_application_count() -> None:
    requirement = _requirement(minimum=2)
    claims = (
        RotationTankTauntActionClaim("taunt_01", 10.5, 0, bar="front"),
        RotationTankTauntActionClaim("taunt_01", 11.5, 0, bar="front"),
    )

    projection = _service().project(
        candidate=_candidate(),
        requirements=(requirement,),
        claims=claims,
        slot_requirements=(_slot("front"),),
    )

    assert projection.resolved is True
    assert projection.inserted_claims == claims
