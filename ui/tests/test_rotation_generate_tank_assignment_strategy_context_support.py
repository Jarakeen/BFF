from types import SimpleNamespace

from ui.rotation_generate_tank_assignment_context_support import (
    RotationGenerateTankAssignmentContextSupport,
    RotationGenerateTankAssignmentEvidence,
)


class _Adapter:
    def adapt(self, _build, *, character_id=None):
        return SimpleNamespace(build=object(), unresolved=())


class _BundleService:
    def compose(self, **_kwargs):
        return SimpleNamespace(
            encounter_id="taleria_hm",
            taunt_application_requirements=("apply",),
            taunt_maintenance_requirements=("maintain",),
            defensive_obligations=("block",),
        )


def test_assignment_context_preserves_explicit_tank_strategy_without_inference():
    taunt_claim = object()
    maintenance_policy = object()
    defensive_claim = object()
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(),
        bundle_service=_BundleService(),
        database_path="eso.db",
    )
    support.set_evidence(
        (
            RotationGenerateTankAssignmentEvidence(
                encounter_id="taleria_hm",
                member_id="tank-a",
                defensive_obligations=(object(),),
                taunt_application_claims=(taunt_claim,),
                taunt_maintenance_refresh_policies=(maintenance_policy,),
                defensive_claims=(defensive_claim,),
            ),
        )
    )

    result = support.context_for(
        object(),
        SimpleNamespace(encounter_id="taleria_hm"),
    )

    assert result.taunt_application_claims == (taunt_claim,)
    assert result.taunt_maintenance_policies == (maintenance_policy,)
    assert result.defensive_claims == (defensive_claim,)


def test_assignment_context_does_not_invent_tank_strategy_when_only_obligations_exist():
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(),
        bundle_service=_BundleService(),
        database_path="eso.db",
    )
    support.set_evidence(
        (
            RotationGenerateTankAssignmentEvidence(
                encounter_id="taleria_hm",
                member_id="tank-a",
                defensive_obligations=(object(),),
            ),
        )
    )

    result = support.context_for(
        object(),
        SimpleNamespace(encounter_id="taleria_hm"),
    )

    assert result.taunt_application_claims == ()
    assert result.taunt_maintenance_policies == ()
    assert result.defensive_claims == ()
