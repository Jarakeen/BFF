from types import SimpleNamespace

import pytest

from ui.rotation_generate_tank_assignment_context_support import (
    RotationGenerateTankAssignmentContextSupport,
    RotationGenerateTankAssignmentEvidence,
)


class _Adapter:
    def adapt(self, _build, *, character_id=None):
        return SimpleNamespace(build=object(), unresolved=())


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


class _DefensiveBundleService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def project(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _guide(encounter_id="taleria_hm"):
    return SimpleNamespace(encounter_id=encounter_id)


def _bundle(encounter_id="taleria_hm"):
    return SimpleNamespace(encounter_id=encounter_id)


def _obligation(obligation_id="block-heavy", *, start=10.0, end=11.0):
    return SimpleNamespace(
        obligation_id=obligation_id,
        window_start_seconds=start,
        window_end_seconds=end,
    )


def test_reviewed_defensive_fact_and_timing_inputs_are_derived_at_generate_time():
    assignment_bundle = _AssignmentBundleService()
    obligation = _obligation()
    defensive_bundle = _DefensiveBundleService(
        SimpleNamespace(obligations=(obligation,), unresolved=())
    )
    support = RotationGenerateTankAssignmentContextSupport(
        database_path="eso.db",
        build_adapter=_Adapter(),
        bundle_service=assignment_bundle,
        defensive_bundle_service=defensive_bundle,
    )
    guide = _guide()
    fact = object()
    policy = object()
    support.set_evidence(
        (
            RotationGenerateTankAssignmentEvidence(
                encounter_id="taleria_hm",
                member_id="tank-a",
                defensive_guide=guide,
                defensive_facts=(fact,),
                defensive_timing_policies=(policy,),
            ),
        )
    )

    result = support.context_for(object(), _bundle())

    assert result.defensive_obligations == (obligation,)
    assert defensive_bundle.calls == [
        {
            "guide": guide,
            "facts": (fact,),
            "policies": (policy,),
        }
    ]
    assert assignment_bundle.calls[0]["defensive_obligations"] == (obligation,)


def test_unresolved_reviewed_defensive_projection_fails_closed_before_assignment_bundle():
    assignment_bundle = _AssignmentBundleService()
    defensive_bundle = _DefensiveBundleService(
        SimpleNamespace(
            obligations=(),
            unresolved=("heavy_01: reviewed defensive fact is missing",),
        )
    )
    support = RotationGenerateTankAssignmentContextSupport(
        database_path="eso.db",
        build_adapter=_Adapter(),
        bundle_service=assignment_bundle,
        defensive_bundle_service=defensive_bundle,
    )
    support.set_evidence(
        (
            RotationGenerateTankAssignmentEvidence(
                encounter_id="taleria_hm",
                member_id="tank-a",
                defensive_guide=_guide(),
                defensive_facts=(object(),),
                defensive_timing_policies=(object(),),
            ),
        )
    )

    with pytest.raises(ValueError, match="reviewed defensive fact is missing"):
        support.context_for(object(), _bundle())

    assert assignment_bundle.calls == []


def test_explicit_and_reviewed_defensive_paths_cannot_compete():
    with pytest.raises(ValueError, match="either explicit obligations or reviewed encounter projection"):
        RotationGenerateTankAssignmentEvidence(
            encounter_id="taleria_hm",
            member_id="tank-a",
            defensive_obligations=(_obligation(),),
            defensive_guide=_guide(),
            defensive_facts=(object(),),
            defensive_timing_policies=(object(),),
        )


def test_reviewed_defensive_inputs_require_matching_encounter_guide():
    with pytest.raises(ValueError, match="guide encounter does not match"):
        RotationGenerateTankAssignmentEvidence(
            encounter_id="taleria_hm",
            member_id="tank-a",
            defensive_guide=_guide("xalvakka_hm"),
            defensive_facts=(object(),),
            defensive_timing_policies=(object(),),
        )


def test_reviewed_defensive_inputs_require_explicit_timing_policy():
    with pytest.raises(ValueError, match="requires timing policies"):
        RotationGenerateTankAssignmentEvidence(
            encounter_id="taleria_hm",
            member_id="tank-a",
            defensive_guide=_guide(),
            defensive_facts=(object(),),
        )
