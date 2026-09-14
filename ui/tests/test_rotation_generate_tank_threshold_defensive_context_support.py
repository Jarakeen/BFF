from types import SimpleNamespace

import pytest

from ui.rotation_generate_tank_assignment_context_support import (
    RotationGenerateTankAssignmentContextSupport,
    RotationGenerateTankAssignmentEvidence,
)


class _Adapter:
    def __init__(self, build):
        self.build = build

    def adapt(self, _saved):
        return SimpleNamespace(build=self.build, unresolved=())


class _AssignmentBundleService:
    def __init__(self):
        self.calls = []

    def compose(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            encounter_id=kwargs["encounter_id"],
            taunt_application_requirements=(),
            taunt_maintenance_requirements=(),
            defensive_obligations=tuple(kwargs["defensive_obligations"]),
        )


class _ThresholdDefensiveBundleService:
    def __init__(self, *, obligations=("threshold-block",), unresolved=()):
        self.obligations = obligations
        self.unresolved = unresolved
        self.calls = []

    def project(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            obligations=self.obligations,
            unresolved=self.unresolved,
        )


def _row():
    return RotationGenerateTankAssignmentEvidence(
        encounter_id="taleria_hm",
        member_id="tank-a",
        defensive_facts=(object(),),
        defensive_threshold_timing_policies=(object(),),
    )


def _bundle(*, thresholds=object()):
    return SimpleNamespace(
        encounter_id="taleria_hm",
        health_threshold_projection=thresholds,
    )


def test_threshold_defensive_projection_flows_into_tank_generate_hard_obligations():
    canonical_build = object()
    assignment_bundle = _AssignmentBundleService()
    threshold_service = _ThresholdDefensiveBundleService()
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(canonical_build),
        bundle_service=assignment_bundle,
        threshold_defensive_bundle_service=threshold_service,
        database_path="eso.db",
    )
    row = _row()
    support.set_evidence((row,))
    thresholds = object()

    result = support.context_for(object(), _bundle(thresholds=thresholds))

    assert result.defensive_obligations == ("threshold-block",)
    assert len(threshold_service.calls) == 1
    threshold_call = threshold_service.calls[0]
    assert threshold_call["thresholds"] is thresholds
    assert threshold_call["facts"] == row.defensive_facts
    assert threshold_call["policies"] == row.defensive_threshold_timing_policies
    assert assignment_bundle.calls[0]["defensive_obligations"] == ("threshold-block",)


def test_threshold_defensive_generate_fails_closed_without_canonical_threshold_projection():
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(object()),
        bundle_service=_AssignmentBundleService(),
        threshold_defensive_bundle_service=_ThresholdDefensiveBundleService(),
        database_path="eso.db",
    )
    support.set_evidence((_row(),))

    with pytest.raises(ValueError, match="canonical health-threshold projection is unavailable"):
        support.context_for(object(), _bundle(thresholds=None))


def test_threshold_defensive_generate_propagates_unresolved_reviewed_projection():
    support = RotationGenerateTankAssignmentContextSupport(
        build_adapter=_Adapter(object()),
        bundle_service=_AssignmentBundleService(),
        threshold_defensive_bundle_service=_ThresholdDefensiveBundleService(
            obligations=(),
            unresolved=("phase_2: threshold time unresolved",),
        ),
        database_path="eso.db",
    )
    support.set_evidence((_row(),))

    with pytest.raises(ValueError, match="threshold time unresolved"):
        support.context_for(object(), _bundle())
