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


def test_oaxiltso_generic_actions_are_compliance_not_provider_requirements():
    evaluator = EncounterRequirementEvaluator(_service())
    roster = ("tank", "healer", "dd1", "dd2")
    evidence = (
        # Even explicit build evidence must not transform a generic encounter
        # action into a provider requirement without stronger encounter semantics.
        RosterCapabilityEvidence("healer", "cleanse", CapabilityAssessment.SUPPORTED, "build"),
        RosterCapabilityEvidence("dd1", "movement", CapabilityAssessment.SUPPORTED, "caller"),
    )

    result = evaluator.evaluate("oaxiltso", roster, evidence)
    sludge = [row for row in result.results if row.mechanic_name == "Noxious Sludge"]
    by_type = {row.requirement_type: row for row in sludge}

    for requirement_type in ("cleanse", "movement", "positioning"):
        row = by_type[requirement_type]
        assert row.semantics == RequirementSemantics.COMPLIANCE
        assert row.classification == CoverageClassification.UNKNOWN
        assert row.providers == ()
        assert row.unknown_members == roster

    assert result.is_fully_evaluable is False
    assert result.is_fully_covered is False


def test_missing_compliance_evidence_is_unknown_not_missing():
    evaluator = EncounterRequirementEvaluator(_service())
    roster = ("tank", "healer")

    result = evaluator.evaluate("oaxiltso", roster)
    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")

    assert cleanse.semantics == RequirementSemantics.COMPLIANCE
    assert cleanse.classification == CoverageClassification.UNKNOWN
    assert cleanse.providers == ()
    assert cleanse.unknown_members == roster


def test_fully_assessed_build_absence_cannot_turn_generic_cleanse_into_missing():
    evaluator = EncounterRequirementEvaluator(_service())
    roster = ("tank", "healer")
    evidence = tuple(
        RosterCapabilityEvidence(member, "cleanse", CapabilityAssessment.UNSUPPORTED, "build")
        for member in roster
    )

    result = evaluator.evaluate("oaxiltso", roster, evidence)
    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")

    assert cleanse.semantics == RequirementSemantics.COMPLIANCE
    assert cleanse.classification == CoverageClassification.UNKNOWN
    assert cleanse.is_actionable_problem is False


def test_multiple_build_cleanse_sources_do_not_create_fake_redundant_provider_coverage():
    evaluator = EncounterRequirementEvaluator(_service())
    roster = ("healer1", "healer2")
    evidence = (
        RosterCapabilityEvidence("healer1", "cleanse", CapabilityAssessment.SUPPORTED, "build"),
        RosterCapabilityEvidence("healer2", "cleanse", CapabilityAssessment.SUPPORTED, "build"),
    )

    result = evaluator.evaluate("oaxiltso", roster, evidence)
    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")

    assert cleanse.classification == CoverageClassification.UNKNOWN
    assert cleanse.providers == ()


def test_generic_interrupt_is_compliance_even_when_build_evidence_conflicts(tmp_path):
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

    assert row.semantics == RequirementSemantics.COMPLIANCE
    assert row.classification == CoverageClassification.UNKNOWN
    assert row.conflicting_members == ()
    assert row.is_actionable_problem is False


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
