from types import SimpleNamespace

import pytest

from ui.rotation_generate_tank_assignment_context_support import (
    RotationGenerateTankAssignmentContextSupport,
    RotationGenerateTankAssignmentEvidence,
)


class _Adapter:
    def __init__(self, adaptation):
        self.adaptation = adaptation
        self.calls = []

    def adapt(self, build, *, character_id=None):
        self.calls.append((build, character_id))
        return self.adaptation


class _BundleService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def compose(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _row(encounter_id="taleria_hm", member_id="tank-a"):
    return RotationGenerateTankAssignmentEvidence(
        encounter_id=encounter_id,
        member_id=member_id,
        assignments=(object(),),
        taunt_policies=(object(),),
        taunt_maintenance_policies=(object(),),
        defensive_obligations=(object(),),
    )


def _bundle(encounter_id="taleria_hm"):
    return SimpleNamespace(encounter_id=encounter_id)


def _derived():
    return SimpleNamespace(
        encounter_id="taleria_hm",
        taunt_application_requirements=("apply",),
        taunt_maintenance_requirements=("maintain",),
        defensive_obligations=("block",),
    )


def test_context_is_derived_from_selected_encounter_and_current_saved_build():
    canonical_build = object()
    adapter = _Adapter(SimpleNamespace(build=canonical_build, unresolved=()))
    bundle_service = _BundleService(_derived())
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=adapter,
        bundle_service=bundle_service,
        database_path="eso.db",
    )
    evidence = _row()
    support.set_evidence((evidence,))
    saved_build = object()

    result = support.context_for(saved_build, _bundle())

    assert result.encounter_id == "taleria_hm"
    assert result.taunt_application_requirements == ("apply",)
    assert result.taunt_maintenance_requirements == ("maintain",)
    assert result.defensive_obligations == ("block",)
    assert adapter.calls == [(saved_build, None)]
    call = bundle_service.calls[0]
    assert call["build"] is canonical_build
    assert call["member_id"] == "tank-a"
    assert call["encounter_id"] == "taleria_hm"
    assert call["assignments"] == evidence.assignments
    assert call["taunt_policies"] == evidence.taunt_policies
    assert call["taunt_maintenance_policies"] == evidence.taunt_maintenance_policies
    assert call["defensive_obligations"] == evidence.defensive_obligations


def test_other_encounter_evidence_is_not_reused_for_selected_boss():
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(SimpleNamespace(build=object(), unresolved=())),
        bundle_service=_BundleService(_derived()),
        database_path="eso.db",
    )
    support.set_evidence((_row("xalvakka_hm"),))

    assert support.context_for(object(), _bundle("taleria_hm")) is None


def test_unresolved_saved_build_adaptation_fails_closed_before_assignment_projection():
    bundle_service = _BundleService(_derived())
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(
            SimpleNamespace(build=None, unresolved=("ambiguous saved skill identity",))
        ),
        bundle_service=bundle_service,
        database_path="eso.db",
    )
    support.set_evidence((_row(),))

    with pytest.raises(ValueError, match="saved-build adaptation is unresolved"):
        support.context_for(object(), _bundle())

    assert bundle_service.calls == []


def test_duplicate_encounter_member_rows_are_rejected():
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(SimpleNamespace(build=object(), unresolved=())),
        bundle_service=_BundleService(_derived()),
        database_path="eso.db",
    )

    with pytest.raises(ValueError, match="duplicate Tank Generate assignment evidence"):
        support.set_evidence((_row(), _row()))


def test_multiple_members_for_same_encounter_fail_closed_until_member_selection_is_explicit():
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(SimpleNamespace(build=object(), unresolved=())),
        bundle_service=_BundleService(_derived()),
        database_path="eso.db",
    )
    support.set_evidence((_row(member_id="tank-a"), _row(member_id="tank-b")))

    with pytest.raises(ValueError, match="member identity must be unambiguous"):
        support.context_for(object(), _bundle())


def test_install_exposes_assignment_evidence_setter_and_context_provider():
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(SimpleNamespace(build=object(), unresolved=())),
        bundle_service=_BundleService(_derived()),
        database_path="eso.db",
    )
    page = SimpleNamespace()

    support.install(page)
    page.set_rotation_generate_tank_assignment_evidence((_row(),))
    result = page.rotation_generate_tank_assignment_context(object(), _bundle())

    assert result.encounter_id == "taleria_hm"
