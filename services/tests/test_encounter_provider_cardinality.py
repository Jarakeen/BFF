from __future__ import annotations

import pytest

from minmax.coverage_classification import CoverageClassification
from services.encounter_requirement_evaluation import (
    CapabilityAssessment,
    EncounterRequirementEvaluator,
    RequirementSemantics,
    RosterCapabilityEvidence,
)
from services.encounter_service import EncounterRequirement


class _RequirementService:
    def __init__(self, requirement: EncounterRequirement) -> None:
        self.requirement = requirement

    def requirements(self, encounter_id: str):
        assert encounter_id == self.requirement.encounter_id
        return (self.requirement,)


def _requirement(*, target_count: int | None = None) -> EncounterRequirement:
    return EncounterRequirement(
        requirement_id="fixture:requirement:group_cleanse",
        encounter_id="fixture",
        mechanic_id="fixture:mechanic",
        mechanic_name="Fixture Mechanic",
        requirement_type="group_cleanse",
        target_count=target_count,
        interpretation_status="structured",
    )


def _evaluator(required: int = 2, *, target_count: int | None = None):
    requirement = _requirement(target_count=target_count)
    evaluator = EncounterRequirementEvaluator(
        _RequirementService(requirement),
        {"group_cleanse": RequirementSemantics.PROVIDER_CAPABILITY},
        {requirement.requirement_id: required},
    )
    return evaluator


def _evidence(member: str, assessment: CapabilityAssessment) -> RosterCapabilityEvidence:
    return RosterCapabilityEvidence(member, "group_cleanse", assessment, "fixture")


def test_exact_required_provider_count_is_covered():
    result = _evaluator().evaluate(
        "fixture",
        ("h1", "h2"),
        (
            _evidence("h1", CapabilityAssessment.SUPPORTED),
            _evidence("h2", CapabilityAssessment.SUPPORTED),
        ),
    ).results[0]

    assert result.required_provider_count == 2
    assert result.classification == CoverageClassification.COVERED
    assert result.providers == ("h1", "h2")


def test_extra_provider_is_redundant_relative_to_explicit_cardinality():
    result = _evaluator().evaluate(
        "fixture",
        ("h1", "h2", "h3"),
        tuple(_evidence(member, CapabilityAssessment.SUPPORTED) for member in ("h1", "h2", "h3")),
    ).results[0]

    assert result.classification == CoverageClassification.REDUNDANT
    assert len(result.providers) == 3


def test_fully_assessed_roster_below_required_count_is_insufficient():
    result = _evaluator().evaluate(
        "fixture",
        ("h1", "dd"),
        (
            _evidence("h1", CapabilityAssessment.SUPPORTED),
            _evidence("dd", CapabilityAssessment.UNSUPPORTED),
        ),
    ).results[0]

    assert result.classification == CoverageClassification.INSUFFICIENT
    assert result.providers == ("h1",)
    assert result.unknown_members == ()


def test_zero_providers_in_fully_assessed_roster_is_missing():
    result = _evaluator().evaluate(
        "fixture",
        ("h1", "h2"),
        (
            _evidence("h1", CapabilityAssessment.UNSUPPORTED),
            _evidence("h2", CapabilityAssessment.UNSUPPORTED),
        ),
    ).results[0]

    assert result.classification == CoverageClassification.MISSING
    assert result.providers == ()


def test_unresolved_member_prevents_premature_insufficient_classification():
    result = _evaluator().evaluate(
        "fixture",
        ("h1", "h2"),
        (
            _evidence("h1", CapabilityAssessment.SUPPORTED),
            _evidence("h2", CapabilityAssessment.UNKNOWN),
        ),
    ).results[0]

    assert result.classification == CoverageClassification.UNKNOWN
    assert result.providers == ("h1",)
    assert result.unknown_members == ("h2",)


def test_target_count_never_becomes_provider_cardinality():
    result = _evaluator(required=1, target_count=2).evaluate(
        "fixture",
        ("h1",),
        (_evidence("h1", CapabilityAssessment.SUPPORTED),),
    ).results[0]

    assert result.target_count == 2
    assert result.required_provider_count == 1
    assert result.classification == CoverageClassification.COVERED


def test_invalid_provider_cardinality_is_rejected():
    requirement = _requirement()
    with pytest.raises(ValueError, match="positive integers"):
        EncounterRequirementEvaluator(
            _RequirementService(requirement),
            {"group_cleanse": RequirementSemantics.PROVIDER_CAPABILITY},
            {requirement.requirement_id: 0},
        )
