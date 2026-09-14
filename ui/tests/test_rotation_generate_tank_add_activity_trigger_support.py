from types import SimpleNamespace

from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterBoundResponsibility,
)
from services.raid_tank_encounter_responsibility_lane_service import (
    RaidTankEncounterResponsibility,
)
from ui.rotation_generate_tank_role_evidence_support import (
    RotationGenerateTankObligationContext,
    RotationGenerateTankRoleEvidenceSupport,
)


class _TriggerService:
    def __init__(self, result):
        self.result = tuple(result)
        self.calls = []

    def for_responsibilities(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _responsibility():
    return RaidTankEncounterBoundResponsibility(
        encounter_id="xalvakka",
        lane_id="add_handler",
        member_id="tank-b",
        responsibility=RaidTankEncounterResponsibility(
            responsibility_id="pack_encounter_adds",
            target_key="encounter_adds",
            action_type="gather_and_stack_on_boss",
            required_capability_type="taunt",
            source="reviewed fixture",
        ),
    )


def test_generate_attaches_reviewed_add_activity_triggers_as_contextual_metadata():
    trigger = SimpleNamespace(
        encounter_id="xalvakka",
        lane_id="add_handler",
        member_id="tank-b",
        responsibility_id="pack_encounter_adds",
        actor_name="Iron Atronach",
        activity_boundary="earliest_source_or_involving_event",
    )
    trigger_service = _TriggerService((trigger,))
    plan_evidence = SimpleNamespace()
    context = RotationGenerateTankObligationContext(
        encounter_id="xalvakka",
        encounter_responsibilities=(_responsibility(),),
        taunt_application_requirements=(object(),),
    )
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        hard_obligation_factory=lambda *args, **kwargs: object(),
        plan_evidence_factory=lambda **kwargs: plan_evidence,
        add_activity_trigger_service=trigger_service,
    )

    result = support.compose(
        player_build=SimpleNamespace(Role="Tank"),
        evidence_bundle=SimpleNamespace(
            encounter_id="xalvakka",
            resource=object(),
            content_type="trial",
        ),
    )

    assert result.plan_evidence_provider is plan_evidence
    assert plan_evidence.tank_add_activity_triggers == (trigger,)
    assert trigger_service.calls == [
        {
            "encounter_id": "xalvakka",
            "responsibilities": (_responsibility(),),
        }
    ]
    assert not hasattr(plan_evidence, "candidate_projector")


def test_generate_does_not_call_add_activity_service_without_contextual_responsibilities():
    trigger_service = _TriggerService((object(),))
    plan_evidence = SimpleNamespace()
    context = RotationGenerateTankObligationContext(
        encounter_id="xalvakka",
        taunt_application_requirements=(object(),),
    )
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        hard_obligation_factory=lambda *args, **kwargs: object(),
        plan_evidence_factory=lambda **kwargs: plan_evidence,
        add_activity_trigger_service=trigger_service,
    )

    support.compose(
        player_build=SimpleNamespace(Role="Tank"),
        evidence_bundle=SimpleNamespace(
            encounter_id="xalvakka",
            resource=object(),
            content_type="trial",
        ),
    )

    assert trigger_service.calls == []
    assert not hasattr(plan_evidence, "tank_add_activity_triggers")
