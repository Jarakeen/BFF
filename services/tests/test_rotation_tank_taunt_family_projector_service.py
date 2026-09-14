from types import SimpleNamespace

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_candidate_service import RotationTankTauntActionClaim
from services.rotation_tank_taunt_family_projector_service import (
    RotationTankTauntFamilyProjectorService,
)
from services.rotation_tank_taunt_obligation_service import (
    RotationTankTauntApplicationRequirement,
)


def _candidate(candidate_id: str, *actions: RotationAction) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tank",
            build_name="Main Tank",
            duration_seconds=30.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _requirement() -> RotationTankTauntApplicationRequirement:
    return RotationTankTauntApplicationRequirement(
        requirement_id="taunt_01",
        source_skill_name="Pierce Armor",
        window_start_seconds=10.0,
        window_end_seconds=12.0,
        bar="front",
    )


def _slot_requirement() -> RotationActionSlotRequirement:
    return RotationActionSlotRequirement(
        action_name="Pierce Armor",
        allowed_bars=("front",),
        action_kind=RotationActionKind.SKILL,
    )


class _FakeCandidateService:
    def project(self, *, candidate, requirements, claims, slot_requirements):
        assert slot_requirements == (_slot_requirement(),)
        requirement = requirements[0]
        satisfied = any(
            action.kind is RotationActionKind.SKILL
            and action.name == requirement.source_skill_name
            and requirement.window_start_seconds <= action.time_seconds <= requirement.window_end_seconds
            and action.bar == requirement.bar
            for action in candidate.plan.actions
        )
        if satisfied:
            return SimpleNamespace(candidate=candidate, unresolved=())

        claim = claims[0]
        occupied = any(
            action.time_seconds == claim.action_time_seconds
            and action.sequence == claim.action_sequence
            for action in candidate.plan.actions
        )
        if occupied:
            return SimpleNamespace(
                candidate=None,
                unresolved=(
                    f"{claim.requirement_id}: taunt claim slot {claim.action_time_seconds:g}s sequence {claim.action_sequence} is occupied by skill",
                ),
            )

        action = RotationAction(
            claim.action_time_seconds,
            claim.action_sequence,
            claim.action_kind,
            name=requirement.source_skill_name,
            bar=claim.bar,
        )
        plan = RotationPlan(
            character_name=candidate.plan.character_name,
            build_name=candidate.plan.build_name,
            duration_seconds=candidate.plan.duration_seconds,
            actions=candidate.plan.actions + (action,),
            assumptions=candidate.plan.assumptions,
            unresolved=candidate.plan.unresolved,
        )
        return SimpleNamespace(
            candidate=GeneratedRotationCandidate(
                candidate_id=candidate.candidate_id,
                plan=plan,
                refresh_leads=candidate.refresh_leads,
                action_claims=candidate.action_claims,
            ),
            unresolved=(),
        )


def _projector() -> RotationTankTauntFamilyProjectorService:
    return RotationTankTauntFamilyProjectorService(
        requirements=(_requirement(),),
        claims=(
            RotationTankTauntActionClaim(
                requirement_id="taunt_01",
                action_time_seconds=11.0,
                action_sequence=0,
                bar="front",
            ),
        ),
        slot_requirements=(_slot_requirement(),),
        candidate_service=_FakeCandidateService(),
    )


def test_family_projector_inserts_taunt_for_missing_candidate() -> None:
    projected = _projector()(_candidate("needs-taunt"))

    assert projected.candidate_id == "needs-taunt"
    assert projected.plan.unresolved == ()
    assert any(action.name == "Pierce Armor" for action in projected.plan.actions)


def test_family_projector_preserves_candidate_that_already_satisfies_taunt() -> None:
    candidate = _candidate(
        "already-good",
        RotationAction(10.5, 0, RotationActionKind.SKILL, name="Pierce Armor", bar="front"),
        RotationAction(11.0, 0, RotationActionKind.SKILL, name="Heroic Slash", bar="front"),
    )

    projected = _projector()(candidate)

    assert projected.candidate_id == candidate.candidate_id
    assert projected.plan.actions == candidate.plan.actions
    assert projected.plan.unresolved == ()


def test_bad_sibling_projection_becomes_candidate_specific_unresolved() -> None:
    blocked = _candidate(
        "blocked",
        RotationAction(11.0, 0, RotationActionKind.SKILL, name="Heroic Slash", bar="front"),
    )
    valid = _candidate("valid")
    projector = _projector()

    blocked_result = projector(blocked)
    valid_result = projector(valid)

    assert blocked_result.candidate_id == "blocked"
    assert len(blocked_result.plan.unresolved) == 1
    assert "taunt claim slot 11s sequence 0 is occupied by skill" in blocked_result.plan.unresolved[0]
    assert valid_result.candidate_id == "valid"
    assert valid_result.plan.unresolved == ()
    assert any(action.name == "Pierce Armor" for action in valid_result.plan.actions)
