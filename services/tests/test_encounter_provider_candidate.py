from types import SimpleNamespace

import pytest

from minmax.coverage_classification import CoverageClassification
from services.encounter_provider_candidate import (
    EncounterProviderCandidateService,
    ProviderCandidateStatus,
)
from services.encounter_requirement_evaluation import (
    CapabilityAssessment,
    RequirementEvaluation,
    RequirementSemantics,
    RosterCapabilityEvidence,
)
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _audit(member_id: str, character_name: str, build_name: str) -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name=character_name,
        build_name=build_name,
        character_id=member_id,
        resolved_sources=(),
        resolved_effects=(),
        conditional_sources=(),
        unresolved=(),
        capability_unresolved=(),
        boundaries=(),
    )


def _requirement(
    *,
    requirement_id: str = "mechanic-1:requirement:major_force",
    semantics: RequirementSemantics = RequirementSemantics.PROVIDER_CAPABILITY,
    classification: CoverageClassification = CoverageClassification.REDUNDANT,
    providers: tuple[str, ...] = ("char-a", "char-b"),
    unknown_members: tuple[str, ...] = (),
    conflicting_members: tuple[str, ...] = (),
    required_provider_count: int | None = 1,
) -> RequirementEvaluation:
    return RequirementEvaluation(
        requirement_id=requirement_id,
        encounter_id="real-encounter",
        mechanic_id="mechanic-1",
        mechanic_name="Source-backed support check",
        requirement_type="major_force",
        semantics=semantics,
        classification=classification,
        target_count=2,
        providers=providers,
        unknown_members=unknown_members,
        conflicting_members=conflicting_members,
        explanation="Phase 10 result",
        required_provider_count=required_provider_count,
    )


def _report(requirements, evidence=()):
    return SimpleNamespace(
        requirement_evaluation=SimpleNamespace(results=tuple(requirements)),
        capability_evidence=tuple(evidence),
    )


def test_candidate_projection_binds_multiple_viable_providers_to_exact_requirement():
    audits = (
        _audit("char-a", "Magrat", "DF Healer"),
        _audit("char-b", "Susan", "Necro Tank"),
    )
    report = _report(
        (_requirement(),),
        (
            RosterCapabilityEvidence(
                member_id="char-a",
                capability_type="major_force",
                assessment=CapabilityAssessment.SUPPORTED,
                source="Aggressive Horn",
            ),
            RosterCapabilityEvidence(
                member_id="char-b",
                capability_type="major_force",
                assessment=CapabilityAssessment.SUPPORTED,
                source="exact alternate source",
            ),
        ),
    )

    candidate_sets = EncounterProviderCandidateService().candidates(report, audits)

    assert len(candidate_sets) == 1
    candidate_set = candidate_sets[0]
    assert candidate_set.requirement_id == "mechanic-1:requirement:major_force"
    assert candidate_set.required_provider_count == 1
    assert candidate_set.coverage_classification == CoverageClassification.REDUNDANT
    assert [candidate.member_id for candidate in candidate_set.viable] == ["char-a", "char-b"]
    assert candidate_set.viable[0].character_name == "Magrat"
    assert candidate_set.viable[0].build_name == "DF Healer"
    assert candidate_set.viable[0].evidence_sources == ("Aggressive Horn",)


def test_candidate_projection_preserves_unknown_and_conflict_without_reclassifying():
    audits = (
        _audit("char-a", "Magrat", "DF Healer"),
        _audit("char-b", "Susan", "Necro Tank"),
        _audit("char-c", "Third", "Build"),
        _audit("char-d", "Explicitly Unsupported", "Build"),
    )
    requirement = _requirement(
        classification=CoverageClassification.CONFLICT,
        providers=("char-a",),
        unknown_members=("char-b",),
        conflicting_members=("char-c",),
    )

    candidate_set = EncounterProviderCandidateService().candidates(
        _report((requirement,)),
        audits,
    )[0]

    assert candidate_set.coverage_classification == CoverageClassification.CONFLICT
    assert [candidate.status for candidate in candidate_set.candidates] == [
        ProviderCandidateStatus.VIABLE,
        ProviderCandidateStatus.UNRESOLVED,
        ProviderCandidateStatus.CONFLICTING,
    ]
    assert all(candidate.member_id != "char-d" for candidate in candidate_set.candidates)


def test_candidate_projection_ignores_non_provider_requirement_semantics():
    compliance = _requirement(
        semantics=RequirementSemantics.COMPLIANCE,
        classification=CoverageClassification.UNKNOWN,
        providers=(),
        unknown_members=("char-a",),
        required_provider_count=None,
    )

    result = EncounterProviderCandidateService().candidates(
        _report((compliance,)),
        (_audit("char-a", "Magrat", "DF Healer"),),
    )

    assert result == ()


def test_candidate_projection_rejects_duplicate_character_identity():
    audits = (
        _audit("char-a", "Magrat", "DF Healer"),
        _audit("char-a", "Magrat", "Other Build"),
    )

    with pytest.raises(ValueError, match="unique member identities"):
        EncounterProviderCandidateService().candidates(_report((_requirement(),)), audits)
