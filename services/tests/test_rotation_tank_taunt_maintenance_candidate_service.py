from types import SimpleNamespace

from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_taunt_candidate_service import RotationTankTauntCandidateService
from services.rotation_tank_taunt_maintenance_candidate_service import (
    RotationTankTauntMaintenanceCandidateService,
    RotationTankTauntMaintenanceRefreshPolicy,
)
from services.rotation_tank_taunt_maintenance_service import (
    RotationTankTauntMaintenanceRequirement,
    RotationTankTauntMaintenanceService,
)


class _DurationService:
    def __init__(self, duration=15.0):
        self.duration = duration

    def resolve(self, _source_name):
        return SimpleNamespace(
            resolved=True,
            duration_seconds=self.duration,
            evidence=(f"canonical taunt duration {self.duration:g}s",),
            unresolved=(),
        )


class _TauntObligationService:
    def assess(self, *, plan, requirement):
        applications = tuple(
            action
            for action in plan.actions
            if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
            and str(action.name or "").casefold()
            == requirement.source_skill_name.casefold()
            and requirement.window_start_seconds
            <= action.time_seconds
            <= requirement.window_end_seconds
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


def _candidate(*actions, duration=40.0):
    return GeneratedRotationCandidate(
        candidate_id="tank",
        plan=RotationPlan(
            character_name="Tank",
            build_name="Main Tank",
            duration_seconds=duration,
            actions=tuple(actions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _cast(time_seconds, *, target="boss", bar="front", sequence=0, name="Pierce Armor"):
    return RotationAction(
        time_seconds=time_seconds,
        sequence=sequence,
        kind=RotationActionKind.SKILL,
        name=name,
        bar=bar,
        target_key=target,
    )


def _requirement(**overrides):
    values = dict(
        requirement_id="boss_maintenance",
        source_skill_name="Pierce Armor",
        target_key="boss",
        active_start_seconds=0.0,
        active_end_seconds=30.0,
        bar="front",
    )
    values.update(overrides)
    return RotationTankTauntMaintenanceRequirement(**values)


def _policy(**overrides):
    values = dict(
        requirement_id="boss_maintenance",
        refresh_lead_seconds=1.0,
        initial_application_time_seconds=0.0,
        action_sequence=0,
        bar="front",
    )
    values.update(overrides)
    return RotationTankTauntMaintenanceRefreshPolicy(**values)


def _slot(*bars):
    return RotationActionSlotRequirement(
        action_name="Pierce Armor",
        allowed_bars=tuple(bars),
        action_kind=RotationActionKind.SKILL,
    )


def _service(duration=15.0):
    maintenance = RotationTankTauntMaintenanceService(
        "unused.db",
        duration_service=_DurationService(duration),
    )
    candidate = RotationTankTauntCandidateService(
        "unused.db",
        obligation_service=_TauntObligationService(),
    )
    return RotationTankTauntMaintenanceCandidateService(
        "unused.db",
        maintenance_service=maintenance,
        candidate_service=candidate,
    )


def test_refresh_policy_fills_continuous_maintenance_from_explicit_initial_cast():
    projection = _service().project(
        candidate=_candidate(),
        requirements=(_requirement(),),
        policies=(_policy(),),
        slot_requirements=(_slot("front"),),
    )

    assert projection.resolved is True
    assert projection.candidate is not None
    assert [claim.action_time_seconds for claim in projection.inserted_claims] == [
        0.0,
        14.0,
        28.0,
    ]
    assert [action.target_key for action in projection.candidate.plan.actions] == [
        "boss",
        "boss",
        "boss",
    ]


def test_existing_target_correct_casts_are_preserved_and_only_real_gap_is_filled():
    projection = _service().project(
        candidate=_candidate(_cast(0.0), _cast(14.5)),
        requirements=(_requirement(),),
        policies=(_policy(initial_application_time_seconds=None),),
        slot_requirements=(_slot("front"),),
    )

    assert projection.resolved is True
    assert projection.candidate is not None
    assert [claim.action_time_seconds for claim in projection.inserted_claims] == [28.5]
    assert [action.time_seconds for action in projection.candidate.plan.actions] == [
        0.0,
        14.5,
        28.5,
    ]


def test_already_satisfied_maintenance_needs_no_refresh_policy():
    projection = _service().project(
        candidate=_candidate(_cast(0.0), _cast(15.0)),
        requirements=(_requirement(),),
        policies=(),
        slot_requirements=(),
    )

    assert projection.resolved is True
    assert projection.inserted_claims == ()
    assert projection.preserved_requirement_ids == ("boss_maintenance",)


def test_uncovered_start_requires_exact_caller_owned_initial_application_time():
    projection = _service().project(
        candidate=_candidate(),
        requirements=(_requirement(),),
        policies=(_policy(initial_application_time_seconds=None),),
        slot_requirements=(_slot("front"),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "boss_maintenance: maintenance starts uncovered and no exact initial taunt application time was supplied",
    )


def test_refresh_lead_must_be_smaller_than_canonical_duration():
    projection = _service().project(
        candidate=_candidate(),
        requirements=(_requirement(),),
        policies=(_policy(refresh_lead_seconds=15.0),),
        slot_requirements=(_slot("front"),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "boss_maintenance: refresh lead 15s must be smaller than canonical taunt duration 15s",
    )


def test_wrong_target_existing_cast_does_not_count_as_maintenance():
    projection = _service().project(
        candidate=_candidate(_cast(0.0, target="add")),
        requirements=(_requirement(),),
        policies=(_policy(),),
        slot_requirements=(_slot("front"),),
    )

    assert projection.resolved is True
    assert projection.candidate is not None
    assert projection.candidate.plan.actions[0].target_key == "add"
    assert any(action.target_key == "boss" for action in projection.candidate.plan.actions)


def test_refresh_claim_never_displaces_occupied_rotation_slot():
    projection = _service().project(
        candidate=_candidate(
            _cast(0.0),
            RotationAction(
                time_seconds=14.0,
                sequence=0,
                kind=RotationActionKind.SKILL,
                name="Heroic Slash",
                bar="front",
            ),
        ),
        requirements=(_requirement(),),
        policies=(_policy(initial_application_time_seconds=None),),
        slot_requirements=(_slot("front"),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "boss_maintenance:maintenance_refresh:001: taunt claim slot 14s sequence 0 is occupied by skill",
    )


def test_refresh_policy_bar_cannot_contradict_maintenance_requirement():
    projection = _service().project(
        candidate=_candidate(),
        requirements=(_requirement(bar="front"),),
        policies=(_policy(bar="back"),),
        slot_requirements=(_slot("front", "back"),),
    )

    assert projection.candidate is None
    assert projection.unresolved == (
        "boss_maintenance: refresh policy bar back does not match maintenance requirement bar front",
    )


def test_policy_for_unknown_requirement_fails_closed():
    bad = RotationTankTauntMaintenanceRefreshPolicy(
        requirement_id="unknown",
        refresh_lead_seconds=1.0,
        initial_application_time_seconds=0.0,
    )

    try:
        _service().project(
            candidate=_candidate(),
            requirements=(_requirement(),),
            policies=(bad,),
            slot_requirements=(_slot("front"),),
        )
    except ValueError as exc:
        assert "references unknown requirement" in str(exc)
    else:
        raise AssertionError("unknown refresh policy requirement should fail closed")
