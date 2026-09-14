from types import SimpleNamespace

import pytest

from services.rotation_tank_assignment_obligation_bundle_service import (
    RotationTankAssignmentObligationBundleService,
)


class _ProjectionService:
    def __init__(self, requirements):
        self.requirements = tuple(requirements)
        self.calls = []

    def derive(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(requirements=self.requirements)


def _assignment(encounter_id, requirement_id):
    return SimpleNamespace(
        encounter_id=encounter_id,
        requirement_id=requirement_id,
    )


def _policy(encounter_id, requirement_id):
    return SimpleNamespace(
        encounter_id=encounter_id,
        requirement_id=requirement_id,
    )


def test_bundle_filters_assignments_to_selected_encounter_and_composes_all_lanes():
    taunt_requirement = object()
    maintenance_requirement = object()
    defensive = object()
    taunt = _ProjectionService((taunt_requirement,))
    maintenance = _ProjectionService((maintenance_requirement,))
    service = RotationTankAssignmentObligationBundleService(
        taunt_application_service=taunt,
        taunt_maintenance_service=maintenance,
    )

    result = service.compose(
        build=object(),
        member_id="tank-a",
        encounter_id="taleria_hm",
        assignments=(
            _assignment("taleria_hm", "boss_taunt"),
            _assignment("xalvakka_hm", "other_taunt"),
        ),
        taunt_policies=(_policy("taleria_hm", "boss_taunt"),),
        taunt_maintenance_policies=(_policy("taleria_hm", "boss_hold"),),
        defensive_obligations=(defensive,),
    )

    assert result.encounter_id == "taleria_hm"
    assert result.member_id == "tank-a"
    assert result.taunt_application_requirements == (taunt_requirement,)
    assert result.taunt_maintenance_requirements == (maintenance_requirement,)
    assert result.defensive_obligations == (defensive,)
    assert result.has_obligations is True
    assert [row.requirement_id for row in taunt.calls[0]["assignments"]] == [
        "boss_taunt"
    ]
    assert [row.requirement_id for row in maintenance.calls[0]["assignments"]] == [
        "boss_taunt"
    ]


def test_bundle_rejects_policy_for_other_encounter_instead_of_silently_dropping_it():
    service = RotationTankAssignmentObligationBundleService(
        taunt_application_service=_ProjectionService(()),
        taunt_maintenance_service=_ProjectionService(()),
    )

    with pytest.raises(ValueError, match="does not match selected encounter"):
        service.compose(
            build=object(),
            member_id="tank-a",
            encounter_id="taleria_hm",
            assignments=(),
            taunt_policies=(_policy("xalvakka_hm", "boss_taunt"),),
        )


def test_bundle_requires_explicit_member_and_encounter_identity():
    service = RotationTankAssignmentObligationBundleService(
        taunt_application_service=_ProjectionService(()),
        taunt_maintenance_service=_ProjectionService(()),
    )

    with pytest.raises(ValueError, match="encounter_id"):
        service.compose(
            build=object(),
            member_id="tank-a",
            encounter_id="",
            assignments=(),
        )
    with pytest.raises(ValueError, match="member_id"):
        service.compose(
            build=object(),
            member_id="",
            encounter_id="taleria_hm",
            assignments=(),
        )


def test_empty_inputs_remain_explicitly_empty_not_auto_passed():
    service = RotationTankAssignmentObligationBundleService(
        taunt_application_service=_ProjectionService(()),
        taunt_maintenance_service=_ProjectionService(()),
    )

    result = service.compose(
        build=object(),
        member_id="tank-a",
        encounter_id="taleria_hm",
        assignments=(),
    )

    assert result.has_obligations is False
