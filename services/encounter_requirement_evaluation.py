from __future__ import annotations

"""Phase 10 evaluation of Phase 9 encounter requirements against explicit roster evidence.

This layer deliberately distinguishes provider capabilities from execution/compliance
requirements. Missing roster evidence stays UNKNOWN instead of being collapsed into
MISSING. Generic Phase 9 mechanics such as movement, positioning, cleansing, and
interrupting describe what the encounter demands; they do not by themselves prove
that one roster member must provide a special build capability.
"""

from collections.abc import Mapping
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


_DEFAULT_REQUIREMENT_SEMANTICS: dict[str, RequirementSemantics] = {
    "movement": RequirementSemantics.COMPLIANCE,
    "positioning": RequirementSemantics.COMPLIANCE,
    "cleanse": RequirementSemantics.COMPLIANCE,
    "interrupt": RequirementSemantics.COMPLIANCE,
}


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
    required_provider_count: int | None
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
    """Evaluate encounter demands against explicit per-roster-member evidence.

    Phase 9's generic actions default to COMPLIANCE. Callers may register stronger
    source-backed semantics for richer requirement types such as ``group_cleanse``
    or ``ranged_interrupt`` without changing the evaluator itself.

    Provider cardinality is keyed by exact ``requirement_id``. It is deliberately
    separate from a mechanic's ``target_count``: two affected targets do not imply
    that two build providers are required. Provider requirements default to one
    provider unless stronger explicit evidence supplies a different cardinality.
    """

    def __init__(
        self,
        encounter_service: EncounterService,
        requirement_semantics: Mapping[str, RequirementSemantics] | None = None,
        required_provider_counts: Mapping[str, int] | None = None,
    ) -> None:
        self._encounter_service = encounter_service
        semantics = dict(_DEFAULT_REQUIREMENT_SEMANTICS)
        if requirement_semantics:
            for requirement_type, semantic in requirement_semantics.items():
                if not str(requirement_type).strip():
                    raise ValueError("requirement semantic keys must be non-empty")
                if not isinstance(semantic, RequirementSemantics):
                    raise ValueError("requirement semantic values must be RequirementSemantics")
                semantics[str(requirement_type)] = semantic
        self._requirement_semantics = semantics

        provider_counts: dict[str, int] = {}
        if required_provider_counts:
            for requirement_id, count in required_provider_counts.items():
                if not str(requirement_id).strip():
                    raise ValueError("provider cardinality keys must be non-empty requirement ids")
                if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
                    raise ValueError("provider cardinality values must be positive integers")
                provider_counts[str(requirement_id)] = count
        self._required_provider_counts = provider_counts

    def semantics_for(self, requirement_type: str) -> RequirementSemantics:
        return self._requirement_semantics.get(requirement_type, RequirementSemantics.UNKNOWN)

    def required_provider_count_for(self, requirement: EncounterRequirement) -> int | None:
        if self.semantics_for(requirement.requirement_type) != RequirementSemantics.PROVIDER_CAPABILITY:
            return None
        return self._required_provider_counts.get(requirement.requirement_id, 1)

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
        required_provider_count = self.required_provider_count_for(requirement)

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
                required_provider_count=None,
                providers=(),
                unknown_members=roster_members,
                conflicting_members=(),
                explanation=reason,
            )

        assert required_provider_count is not None
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
        elif len(providers) >= required_provider_count:
            extra = len(providers) - required_provider_count
            classification = (
                CoverageClassification.REDUNDANT
                if extra > 0
                else CoverageClassification.COVERED
            )
            explanation = (
                f"{len(providers)} proven provider(s) satisfy the explicit requirement "
                f"for {required_provider_count} provider(s) of {requirement.requirement_type}."
            )
        elif unknown_members:
            classification = CoverageClassification.UNKNOWN
            explanation = (
                f"{len(providers)} proven provider(s) are below the required "
                f"{required_provider_count}, but unresolved roster evidence could still "
                "change the provider count."
            )
        elif providers:
            classification = CoverageClassification.INSUFFICIENT
            explanation = (
                f"Only {len(providers)} proven provider(s) are available; the requirement "
                f"explicitly needs {required_provider_count}."
            )
        else:
            classification = CoverageClassification.MISSING
            explanation = (
                f"Every roster member is explicitly assessed and none support "
                f"{requirement.requirement_type}; {required_provider_count} provider(s) are required."
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
            required_provider_count=required_provider_count,
            providers=tuple(providers),
            unknown_members=tuple(unknown_members),
            conflicting_members=tuple(conflicting_members),
            explanation=explanation,
        )
