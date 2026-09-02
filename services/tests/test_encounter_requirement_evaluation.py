from __future__ import annotations

from pathlib import Path

import pytest

from minmax.coverage_classification import CoverageClassification
from services.encounter_repository import EncounterRepository
from services.encounter_requirement_evaluation import (
    CapabilityAssessment,
    EncounterRequirementEvaluator,
    RequirementSemantics,
    RosterCapabilityEvidence,
)
from services.encounter_service import EncounterService


ROOT = Path(__file__).resolve().parents[2]


def _service(data_root: Path = ROOT / "data") -> EncounterService:
    return EncounterService(EncounterRepository.from_data_root(data_root))


def test_oaxiltso_provider_and_compliance_requirements_remain_semantically_distinct():
    evaluator = EncounterRequirementEvaluator(_service())
    roster = ("tank", "healer", "dd1", "dd2")
    evidence = (
        RosterCapabilityEvidence("healer", "cleanse", CapabilityAssessment.SUPPORTED, "build"),
        RosterCapabilityEvidence("tank", "cleanse", CapabilityAssessment.UNSUPPORTED, "build"),
        RosterCapabilityEvidence("dd1", "cleanse", CapabilityAssessment.UNSUPPORTED, "build"),
        RosterCapabilityEvidence("dd2", "cleanse", CapabilityAssessment.UNSUPPORTED, "build"),
        # Movement evidence must not be mistaken for provider coverage.
        RosterCapabilityEvidence("dd1", "movement", CapabilityAssessment.SUPPORTED, "caller"),
    )

    result = evaluator.evaluate("oaxiltso", roster, evidence)
    sludge = [row for row in result.results if row.mechanic_name == "Noxious Sludge"]
    by_type = {row.requirement_type: row for row in sludge}

    assert by_type["cleanse"].semantics == RequirementSemantics.PROVIDER_CAPABILITY
    assert by_type["cleanse"].classification == CoverageClassification.COVERED
    assert by_type["cleanse"].providers == ("healer",)

    assert by_type["movement"].semantics == RequirementSemantics.COMPLIANCE
    assert by_type["movement"].classification == CoverageClassification.UNKNOWN
    assert by_type["positioning"].classification == CoverageClassification.UNKNOWN
    assert result.is_fully_evaluable is False
    assert result.is_fully_covered is False


def test_missing_evidence_is_unknown_not_missing():
    evaluator = EncounterRequirementEvaluator(_service())
    roster = ("tank", "healer")

    result = evaluator.evaluate("oaxiltso", roster)
    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")

    assert cleanse.classification == CoverageClassification.UNKNOWN
    assert cleanse.providers == ()
    assert cleanse.unknown_members == roster


def test_fully_assessed_provider_absence_is_missing():
    evaluator = EncounterRequirementEvaluator(_service())
    roster = ("tank", "healer")
    evidence = tuple(
        RosterCapabilityEvidence(member, "cleanse", CapabilityAssessment.UNSUPPORTED, "build")
        for member in roster
    )

    result = evaluator.evaluate("oaxiltso", roster, evidence)
    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")

    assert cleanse.classification == CoverageClassification.MISSING
    assert cleanse.unknown_members == ()
    assert cleanse.is_actionable_problem is True


def test_multiple_supported_providers_are_redundant_not_silently_collapsed():
    evaluator = EncounterRequirementEvaluator(_service())
    roster = ("healer1", "healer2")
    evidence = (
        RosterCapabilityEvidence("healer1", "cleanse", CapabilityAssessment.SUPPORTED, "build"),
        RosterCapabilityEvidence("healer2", "cleanse", CapabilityAssessment.SUPPORTED, "build"),
    )

    result = evaluator.evaluate("oaxiltso", roster, evidence)
    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")

    assert cleanse.classification == CoverageClassification.REDUNDANT
    assert cleanse.providers == roster


def test_conflicting_member_evidence_is_conflict(tmp_path):
    boss = tmp_path / "eso_info" / "bosses"
    evidence_root = tmp_path / "encounter_evidence"
    boss.mkdir(parents=True)
    evidence_root.mkdir()
    (boss / "x.json").write_text(
        '{"id":"x","mechanics":['
        '{"name":"Cast","description":"","interruptible":true}'
        ']}',
        encoding="utf-8",
    )
    evaluator = EncounterRequirementEvaluator(_service(tmp_path))
    roster = ("tank",)
    evidence = (
        RosterCapabilityEvidence("tank", "interrupt", CapabilityAssessment.SUPPORTED, "source-a"),
        RosterCapabilityEvidence("tank", "interrupt", CapabilityAssessment.UNSUPPORTED, "source-b"),
    )

    result = evaluator.evaluate("x", roster, evidence)
    row = result.results[0]

    assert row.classification == CoverageClassification.CONFLICT
    assert row.conflicting_members == ("tank",)
    assert row.is_actionable_problem is True


def test_evidence_for_non_roster_member_is_rejected():
    evaluator = EncounterRequirementEvaluator(_service())

    with pytest.raises(ValueError, match="non-roster member"):
        evaluator.evaluate(
            "oaxiltso",
            ("healer",),
            (
                RosterCapabilityEvidence(
                    "not-in-roster",
                    "cleanse",
                    CapabilityAssessment.SUPPORTED,
                    "build",
                ),
            ),
        )
