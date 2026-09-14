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
    def for_responsibilities(self, **_kwargs):
        return ()


class _HandlingService:
    def for_responsibilities(self, **_kwargs):
        return (SimpleNamespace(responsibility_id="boss_taunt", actor_name="Xalvakka"),)


class _PriorityService:
    def __init__(self):
        self.calls = []

    def for_responsibilities(self, **kwargs):
        self.calls.append(kwargs)
        return (SimpleNamespace(priority=10, directive="maintain_primary_boss_ownership"),)


def _responsibility():
    return RaidTankEncounterBoundResponsibility(
        encounter_id="xalvakka",
        lane_id="boss_holder",
        member_id="tank-a",
        responsibility=RaidTankEncounterResponsibility(
            responsibility_id="boss_taunt",
            target_key="xalvakka",
            action_type="maintain_taunt",
            required_capability_type="taunt",
            source="reviewed fixture",
        ),
    )


def test_generate_attaches_ordered_tank_priority_context_without_changing_hard_obligation() -> None:
    plan_evidence = SimpleNamespace()
    responsibility = _responsibility()
    context = RotationGenerateTankObligationContext(
        encounter_id="xalvakka",
        encounter_responsibilities=(responsibility,),
        taunt_application_requirements=(object(),),
    )
    priority_service = _PriorityService()
    handling_service = _HandlingService()
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        hard_obligation_factory=lambda *args, **kwargs: object(),
        plan_evidence_factory=lambda **kwargs: plan_evidence,
        add_activity_trigger_service=_TriggerService(),
        add_taunt_handling_context_service=handling_service,
        priority_context_service=priority_service,
    )

    support.compose(
        player_build=SimpleNamespace(Role="Tank"),
        evidence_bundle=SimpleNamespace(
            encounter_id="xalvakka",
            resource=object(),
            content_type="trial",
        ),
    )

    assert plan_evidence.tank_priority_context[0].priority == 10
    assert plan_evidence.tank_priority_context[0].directive == "maintain_primary_boss_ownership"
    assert not hasattr(plan_evidence, "candidate_projector")
    assert priority_service.calls == [
        {
            "encounter_id": "xalvakka",
            "responsibilities": (responsibility,),
            "handling_context": plan_evidence.tank_add_taunt_handling_context,
        }
    ]
