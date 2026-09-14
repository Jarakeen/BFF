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


def _responsibility():
    return RaidTankEncounterBoundResponsibility(
        encounter_id="xalvakka",
        lane_id="add_handler",
        member_id="tank-b",
        responsibility=RaidTankEncounterResponsibility(
            responsibility_id="daedroth_facing",
            target_key="daedroth",
            action_type="face_away_from_group",
            source="reviewed fixture",
        ),
    )


def test_generate_carries_contextual_tank_responsibility_without_fake_rotation_evaluation():
    plan_evidence = SimpleNamespace()
    hard_obligation = object()
    context = RotationGenerateTankObligationContext(
        encounter_id="xalvakka",
        encounter_responsibilities=(_responsibility(),),
        taunt_application_requirements=(object(),),
    )
    support = RotationGenerateTankRoleEvidenceSupport(
        obligation_context_provider=lambda _build, _bundle: context,
        database_path="eso.db",
        hard_obligation_factory=lambda *args, **kwargs: hard_obligation,
        plan_evidence_factory=lambda **kwargs: plan_evidence,
    )
    build = SimpleNamespace(Role="Tank")
    bundle = SimpleNamespace(
        encounter_id="xalvakka",
        resource=object(),
        content_type="trial",
    )

    result = support.compose(player_build=build, evidence_bundle=bundle)

    assert result.plan_evidence_provider is plan_evidence
    assert plan_evidence.tank_encounter_responsibilities == (_responsibility(),)
    assert not hasattr(plan_evidence, "candidate_projector")


def test_contextual_responsibility_does_not_count_as_rotation_evaluable_hard_obligation():
    context = RotationGenerateTankObligationContext(
        encounter_id="xalvakka",
        encounter_responsibilities=(_responsibility(),),
    )

    assert context.has_contextual_responsibilities is True
    assert context.has_obligations is False
