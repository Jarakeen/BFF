from types import SimpleNamespace

import pytest

from minmax.rotation_action_occupancy import RotationActionOccupancyRequirement
from minmax.rotation_action_slot_legality import RotationActionSlotRequirement
from minmax.rotation_action_target_legality import (
    RotationActionTargetRequirement,
    RotationTargetKind,
    RotationTargetStateWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
from services.rotation_runtime_trigger_condition_service import RotationRuntimeTriggerObservation
from services.rotation_saved_build_action_target_service import RotationSavedBuildActionTargetEvidence
from services.rotation_saved_build_action_slot_service import RotationSavedBuildActionSlotEvidence
from services.rotation_saved_build_action_timing_service import RotationSavedBuildActionTimingEvidence
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext
from ui.rotation_runtime_application_support import (
    RotationRuntimeApplicationSupport,
    install_rotation_runtime_application,
)


def _build() -> PlayerBuild:
    return PlayerBuild(
        Name="Rylonia",
        BuildName="Tank Build",
        Role="Tank",
        FrontBarSkills=["Pierce Armor"],
    )


def _context() -> RotationGenerateCanonicalContext:
    responsibility = RaidPlanTriggeredResponsibility(
        responsibility_id="xalvakka:pack_encounter_adds:iron_atronach",
        seat_id="off-tank",
        encounter_id="xalvakka",
        trigger_key="encounter_actor_active:iron_atronach",
        directive="acquire_and_maintain_owned_add_when_active",
        target_key="Iron Atronach",
        required_capability_type="taunt",
        source="reviewed Tank add activity",
    )
    raid_plan = RaidPlan(
        plan_id="performance-mode-rg",
        trial_id="rockgrove",
        name="Performance Mode - Rockgrove",
        members=(
            RaidPlanMember(
                seat_id="off-tank",
                gamertag="TankPlayer",
                character_id="ryl-id",
                character_name="Rylonia",
                role="Tank",
                selected_build_name="Tank Build",
            ),
        ),
        triggered_responsibilities=(responsibility,),
    )
    return RotationGenerateCanonicalContext(
        evidence_inputs=object(),  # type: ignore[arg-type]
    ).with_raid_plan_member(
        raid_plan=raid_plan,
        seat_id="off-tank",
        build=_build(),
        encounter_id="xalvakka",
    )


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Rylonia",
        build_name="Tank Build",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


class _Pipeline:
    def __init__(self, final_plan: RotationPlan):
        self.final_plan = final_plan
        self.calls = []

    def apply(self, **kwargs):
        self.calls.append(kwargs)
        initial = kwargs["plan"]
        return SimpleNamespace(
            initial_plan=initial,
            final_plan=self.final_plan,
            changed=self.final_plan != initial,
        )


class _TargetService:
    def __init__(self, evidence):
        self.evidence = evidence
        self.calls = []

    def resolve(self, build):
        self.calls.append(build)
        return self.evidence


class _Page:
    def __init__(self, orchestration, rotation_plan=None):
        self.last_canonical_cadence_orchestration_result = orchestration
        self.rotation_plan = rotation_plan
        self.set_calls = []

    def set_rotation_plan(self, plan):
        self.rotation_plan = plan
        self.set_calls.append(plan)


def _orchestration(plan: RotationPlan):
    slot = RotationActionSlotRequirement("Pierce Armor", ("front",))
    occupancy = RotationActionOccupancyRequirement("Pierce Armor", 0.8)
    candidate_result = SimpleNamespace(
        action_slot_evidence=RotationSavedBuildActionSlotEvidence(
            slot_requirements=(slot,),
        ),
        action_timing_evidence=RotationSavedBuildActionTimingEvidence(
            occupancy_requirements=(occupancy,),
        ),
    )
    return SimpleNamespace(
        final_plan=plan,
        canonical_result=SimpleNamespace(candidate_result=candidate_result),
        runtime_triggered_intents=("pending-intent",),
    )


def _observation():
    return RotationRuntimeTriggerObservation(
        trigger_key="encounter_actor_active:iron_atronach",
        observed_at_seconds=37.25,
        source="authoritative runtime actor activity",
        encounter_id="xalvakka",
        source_plan_id="performance-mode-rg",
        source_seat_id="off-tank",
    )


def _window():
    return RotationTargetStateWindow(
        name="iron active",
        start_seconds=37.0,
        end_seconds=60.0,
        target_kind=RotationTargetKind.ENEMY,
    )


def test_runtime_application_forwards_exact_generate_evidence_and_updates_page_plan() -> None:
    original = _plan()
    updated = _plan(
        RotationAction(37.25, 0, RotationActionKind.SKILL, "Pierce Armor", "front", "Iron Atronach")
    )
    pipeline = _Pipeline(updated)
    target_requirement = RotationActionTargetRequirement(
        action_name="Pierce Armor",
        allowed_targets=(RotationTargetKind.ENEMY,),
    )
    targets = _TargetService(
        RotationSavedBuildActionTargetEvidence(target_requirements=(target_requirement,))
    )
    page = _Page(_orchestration(original), rotation_plan=original)

    result = RotationRuntimeApplicationSupport(
        pipeline=pipeline,
        target_service=targets,
    ).apply(
        page,
        context=_context(),
        observations=(_observation(),),
        target_windows=(_window(),),
    )

    assert result.changed is True
    assert page.set_calls == [updated]
    assert page.last_rotation_runtime_application_result is result
    call = pipeline.calls[0]
    assert call["plan"] is original
    assert call["build"].Name == "Rylonia"
    assert call["intents"] == ("pending-intent",)
    assert call["observations"] == (_observation(),)
    assert call["slot_requirements"][0].action_name == "Pierce Armor"
    assert call["occupancy_requirements"][0].action_name == "Pierce Armor"
    assert call["target_requirements"] == (target_requirement,)
    assert call["target_windows"] == (_window(),)
    assert targets.calls[0].BuildName == "Tank Build"


def test_runtime_application_uses_current_materialized_plan_for_later_observations() -> None:
    canonical = _plan()
    current = _plan(
        RotationAction(20.0, 0, RotationActionKind.SKILL, "Pierce Armor", "front", "Earlier Add")
    )
    pipeline = _Pipeline(current)
    page = _Page(_orchestration(canonical), rotation_plan=current)

    RotationRuntimeApplicationSupport(
        pipeline=pipeline,
        target_service=_TargetService(RotationSavedBuildActionTargetEvidence()),
    ).apply(
        page,
        context=_context(),
        observations=(),
        target_windows=(),
    )

    assert pipeline.calls[0]["plan"] is current
    assert page.set_calls == []


def test_runtime_application_rejects_displayed_plan_from_another_build() -> None:
    canonical = _plan()
    wrong = RotationPlan(
        character_name="Somebody Else",
        build_name="Other Build",
        duration_seconds=60.0,
        actions=(),
    )
    support = RotationRuntimeApplicationSupport(
        pipeline=_Pipeline(canonical),
        target_service=_TargetService(RotationSavedBuildActionTargetEvidence()),
    )

    with pytest.raises(ValueError, match="does not belong"):
        support.apply(
            _Page(_orchestration(canonical), rotation_plan=wrong),
            context=_context(),
            observations=(),
            target_windows=(),
        )


def test_runtime_application_requires_frozen_effective_build_context() -> None:
    support = RotationRuntimeApplicationSupport(
        pipeline=_Pipeline(_plan()),
        target_service=_TargetService(RotationSavedBuildActionTargetEvidence()),
    )

    with pytest.raises(ValueError, match="frozen effective-build"):
        support.apply(
            _Page(_orchestration(_plan())),
            context=RotationGenerateCanonicalContext(
                evidence_inputs=object(),  # type: ignore[arg-type]
            ),
            observations=(),
            target_windows=(),
        )


def test_installer_exposes_stable_runtime_observation_application_method() -> None:
    page = _Page(_orchestration(_plan()), rotation_plan=_plan())

    support = install_rotation_runtime_application(page)

    assert page.rotation_runtime_application_support is support
    assert page.last_rotation_runtime_application_result is None
    assert callable(page.apply_runtime_trigger_observations)
