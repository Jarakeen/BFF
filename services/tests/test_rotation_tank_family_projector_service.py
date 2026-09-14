from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_tank_family_projector_service import RotationTankFamilyProjectorService


def _candidate(candidate_id="baseline", *, assumptions=()):
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Tank",
            build_name="Projection",
            duration_seconds=30.0,
            actions=(),
            assumptions=tuple(assumptions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _Stage:
    def __init__(self, label, calls, *, candidate_id=None):
        self.label = label
        self.calls = calls
        self.candidate_id = candidate_id

    def __call__(self, candidate):
        self.calls.append((self.label, candidate.plan.assumptions))
        return _candidate(
            self.candidate_id or candidate.candidate_id,
            assumptions=candidate.plan.assumptions + (self.label,),
        )


def test_composer_runs_only_explicit_strategy_lanes_in_fixed_order():
    calls = []
    service = RotationTankFamilyProjectorService(
        database_path="eso.db",
        taunt_application_requirements=(object(),),
        taunt_application_claims=(object(),),
        taunt_maintenance_requirements=(object(),),
        taunt_maintenance_policies=(object(),),
        defensive_obligations=(object(),),
        defensive_claims=(object(),),
        taunt_projector=_Stage("taunt", calls),
        maintenance_projector=_Stage("maintenance", calls),
        defensive_projector=_Stage("defensive", calls),
    )

    result = service(_candidate())

    assert service.active is True
    assert [label for label, _ in calls] == ["taunt", "maintenance", "defensive"]
    assert result.plan.assumptions == ("taunt", "maintenance", "defensive")


def test_composer_without_strategy_is_inert_and_does_not_infer_actions():
    service = RotationTankFamilyProjectorService(
        database_path="eso.db",
        taunt_application_requirements=(object(),),
        taunt_maintenance_requirements=(object(),),
        defensive_obligations=(object(),),
    )
    candidate = _candidate()

    assert service.active is False
    assert service(candidate) is candidate


def test_strategy_requires_matching_obligation_lane():
    with pytest.raises(ValueError, match="claims require taunt application requirements"):
        RotationTankFamilyProjectorService(
            database_path="eso.db",
            taunt_application_claims=(object(),),
        )

    with pytest.raises(ValueError, match="maintenance policy requires maintenance requirements"):
        RotationTankFamilyProjectorService(
            database_path="eso.db",
            taunt_maintenance_policies=(object(),),
        )

    with pytest.raises(ValueError, match="defensive claims require defensive obligations"):
        RotationTankFamilyProjectorService(
            database_path="eso.db",
            defensive_claims=(object(),),
        )


def test_each_stage_must_preserve_candidate_identity():
    service = RotationTankFamilyProjectorService(
        database_path="eso.db",
        taunt_application_requirements=(object(),),
        taunt_application_claims=(object(),),
        taunt_projector=_Stage("taunt", [], candidate_id="other"),
    )

    with pytest.raises(ValueError, match="preserve candidate identity"):
        service(_candidate())


def test_each_stage_must_return_generated_candidate():
    service = RotationTankFamilyProjectorService(
        database_path="eso.db",
        taunt_application_requirements=(object(),),
        taunt_application_claims=(object(),),
        taunt_projector=lambda candidate: SimpleNamespace(candidate_id=candidate.candidate_id),
    )

    with pytest.raises(TypeError, match="must return GeneratedRotationCandidate"):
        service(_candidate())
