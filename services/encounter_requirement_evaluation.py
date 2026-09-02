from __future__ import annotations

"""Phase 10 evaluation of Phase 9 encounter requirements against explicit roster evidence.

This layer deliberately distinguishes provider capabilities from execution/compliance
requirements. Missing roster evidence stays UNKNOWN instead of being collapsed into
MISSING. Generic Phase 9 mechanics such as movement, positioning, cleansing, and
interrupting describe what the encounter demands; they do not by themselves prove
that one roster member must provide a special build capability.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.coverage_classification import CoverageClassification
from services.encounter_service import EncounterRequirement, EncounterService


class RequirementSemantics(str, Enum):
    PROVIDER_CAPABILITY = "provider_capability"
    COMPLIANCE = "compliance"
    UNKNOWN = "unknown"


class CapabilityAssessment(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


# Phase 9 currently exposes these as generic encounter actions. Do not turn them
# into special provider requirements without stronger encounter evidence, e.g.
# explicit ranged-interrupt, group-cleanse, or named-effect requirements.
_PROVIDER_REQUIREMENTS = frozenset()
_COMPLIANCE_REQUIREMENTS = frozenset({"movement", "positioning", "cleanse", "interrupt"})


@dataclass(frozen=True)
class RosterCapabilityEvidence:
    member_id: str
    capability_type: str
    assessment: CapabilityAssessment
    source: str = ""

    def __post_init__(self) -> None:
        if not self.member_id:
            raise ValueError("member_id must be non-empty")
        if not self.capability_type:
            raise ValueError("capability_type must be non-empty")


@dataclass(frozen=True)
class RequirementEvaluation:
    requirement_id: str
    encounter_id: str
    mechanic_id: str
    mechanic_name: str
    requirement_type: str
    semantics: RequirementSemantics
    classification: CoverageClassification
    target_count: int | None
    providers: tuple[str, ...]
    unknown_members: tuple[str, ...]
    conflicting_members: tuple[str, ...]
    explanation: str

    @property
    def is_satisfied(self) -> bool:
        return self.classification in {
            CoverageClassification.COVERED,
            CoverageClassification.REDUNDANT,
            CoverageClassification.RESILIENT,
        }

    @property
    def is_actionable_problem(self) -> bool:
        return self.classification in {
            CoverageClassification.MISSING,
            CoverageClassification.INSUFFICIENT,
            CoverageClassification.CONFLICT,
        }


@dataclass(frozen=True)
class EncounterRequirementEvaluation:
    encounter_id: str
    results: tuple[RequirementEvaluation, ...]

    @property
    def unknown(self) -> tuple[RequirementEvaluation, ...]:
        return tuple(
            result
            for result in self.results
            if result.classification == CoverageClassification.UNKNOWN
        )

    @property
    def problems(self) -> tuple[RequirementEvaluation, ...]:
        return tuple(result for result in self.results if result.is_actionable_problem)

    @property
    def satisfied(self) -> tuple[RequirementEvaluation, ...]:
        return tuple(result for result in self.results if result.is_satisfied)

    @property
    def is_fully_evaluable(self) -> bool:
        return not self.unknown

    @property
    def is_fully_covered(self) -> bool:
        return self.is_fully_evaluable and not self.problems


class EncounterRequirementEvaluator:
    """Evaluate Phase 9 demands against explicit per-roster-member evidence."""

    def __init__(self, encounter_service: EncounterService) -> None:
        self._encounter_service = encounter_service

    @staticmethod
    def semantics_for(requirement_type: str) -> RequirementSemantics:
        if requirement_type in _PROVIDER_REQUIREMENTS:
            return RequirementSemantics.PROVIDER_CAPABILITY
        if requirement_type in _COMPLIANCE_REQUIREMENTS:
            return RequirementSemantics.COMPLIANCE
        return RequirementSemantics.UNKNOWN

    def evaluate(
        self,
        encounter_id: str,
        roster_members: tuple[str, ...],
        evidence: tuple[RosterCapabilityEvidence, ...] = (),
    ) -> EncounterRequirementEvaluation:
        if len(roster_members) != len(set(roster_members)):
            raise ValueError("roster_members must contain unique member ids")
        if any(not member_id for member_id in roster_members):
            raise ValueError("roster member ids must be non-empty")

        roster_set = set(roster_members)
        for row in evidence:
            if row.member_id not in roster_set:
                raise ValueError(
                    f"Capability evidence references non-roster member {row.member_id!r}"
                )

        results = tuple(
            self._evaluate_requirement(requirement, roster_members, evidence)
            for requirement in self._encounter_service.requirements(encounter_id)
        )
        return EncounterRequirementEvaluation(encounter_id=encounter_id, results=results)

    def _evaluate_requirement(
        self,
        requirement: EncounterRequirement,
        roster_members: tuple[str, ...],
        evidence: tuple[RosterCapabilityEvidence, ...],
    ) -> RequirementEvaluation:
        semantics = self.semantics_for(requirement.requirement_type)

        if semantics != RequirementSemantics.PROVIDER_CAPABILITY:
            reason = (
                "Execution/compliance requirement requires explicit compliance evidence; "
                "provider capability is not inferred from a generic encounter action."
                if semantics == RequirementSemantics.COMPLIANCE
                else "Requirement semantics are not yet mapped for Phase 10 evaluation."
            )
            return RequirementEvaluation(
                requirement_id=requirement.requirement_id,
                encounter_id=requirement.encounter_id,
                mechanic_id=requirement.mechanic_id,
                mechanic_name=requirement.mechanic_name,
                requirement_type=requirement.requirement_type,
                semantics=semantics,
                classification=CoverageClassification.UNKNOWN,
                target_count=requirement.target_count,
                providers=(),
                unknown_members=roster_members,
                conflicting_members=(),
                explanation=reason,
            )

        rows_by_member: dict[str, list[RosterCapabilityEvidence]] = {
            member_id: [] for member_id in roster_members
        }
        for row in evidence:
            if row.capability_type == requirement.requirement_type:
                rows_by_member[row.member_id].append(row)

        providers: list[str] = []
        unknown_members: list[str] = []
        conflicting_members: list[str] = []

        for member_id in roster_members:
            rows = rows_by_member[member_id]
            if not rows:
                unknown_members.append(member_id)
                continue
            assessments = {row.assessment for row in rows}
            if len(assessments) > 1:
                conflicting_members.append(member_id)
                continue
            assessment = next(iter(assessments))
            if assessment == CapabilityAssessment.SUPPORTED:
                providers.append(member_id)
            elif assessment == CapabilityAssessment.UNKNOWN:
                unknown_members.append(member_id)

        if conflicting_members:
            classification = CoverageClassification.CONFLICT
            explanation = "Conflicting capability evidence exists for one or more roster members."
        elif providers:
            classification = (
                CoverageClassification.REDUNDANT
                if len(providers) > 1
                else CoverageClassification.COVERED
            )
            explanation = (
                f"{len(providers)} roster member(s) have explicit support for "
                f"{requirement.requirement_type}."
            )
        elif unknown_members:
            classification = CoverageClassification.UNKNOWN
            explanation = (
                "No supported provider is proven, but one or more roster members "
                "still have unresolved capability evidence."
            )
        else:
            classification = CoverageClassification.MISSING
            explanation = (
                f"Every roster member is explicitly assessed and none support "
                f"{requirement.requirement_type}."
            )

        return RequirementEvaluation(
            requirement_id=requirement.requirement_id,
            encounter_id=requirement.encounter_id,
            mechanic_id=requirement.mechanic_id,
            mechanic_name=requirement.mechanic_name,
            requirement_type=requirement.requirement_type,
            semantics=semantics,
            classification=classification,
            target_count=requirement.target_count,
            providers=tuple(providers),
            unknown_members=tuple(unknown_members),
            conflicting_members=tuple(conflicting_members),
            explanation=explanation,
        )
