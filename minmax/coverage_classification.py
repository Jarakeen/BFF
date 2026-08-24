from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CoverageClassification(str, Enum):
    """
    Actionable interpretation of an encounter capability requirement.

    These classifications describe the state of the requirement from the
    roster's perspective. They do not prescribe a roster change.
    """

    COVERED = "covered"
    REDUNDANT = "redundant"
    RESILIENT = "resilient"
    INSUFFICIENT = "insufficient"
    MISSING = "missing"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CoverageClassificationResult:
    """
    Actionable classification for one encounter capability requirement.

    This is deliberately separate from CoverageGap and ProviderConflict.
    Those models describe evidence; this model interprets that evidence
    into a concise operational state.
    """

    effect_name: str
    classification: CoverageClassification

    required_provider_count: int
    valid_provider_count: int

    providers: tuple[str, ...] = ()
    redundant_providers: tuple[str, ...] = ()
    resilient_providers: tuple[str, ...] = ()
    conflicting_providers: tuple[str, ...] = ()

    explanation: str = ""

    @property
    def is_actionable_problem(self) -> bool:
        """
        Whether this classification identifies something that requires
        attention for the current requirement.
        """
        return self.classification in {
            CoverageClassification.MISSING,
            CoverageClassification.INSUFFICIENT,
            CoverageClassification.CONFLICT,
        }

    @property
    def is_satisfied(self) -> bool:
        """Whether the requirement is currently satisfied."""
        return self.classification in {
            CoverageClassification.COVERED,
            CoverageClassification.REDUNDANT,
            CoverageClassification.RESILIENT,
        }


@dataclass(frozen=True)
class CoverageClassificationReport:
    """Read-only collection of actionable capability classifications."""

    results: tuple[CoverageClassificationResult, ...]

    def all(self) -> tuple[CoverageClassificationResult, ...]:
        return self.results

    def for_effect(
        self,
        effect_name: str,
    ) -> CoverageClassificationResult | None:
        for result in self.results:
            if result.effect_name == effect_name:
                return result

        return None

    @property
    def problems(self) -> tuple[CoverageClassificationResult, ...]:
        return tuple(
            result
            for result in self.results
            if result.is_actionable_problem
        )

    @property
    def satisfied(self) -> tuple[CoverageClassificationResult, ...]:
        return tuple(
            result
            for result in self.results
            if result.is_satisfied
        )


class CoverageClassificationAnalyzer:
    """
    Convert coverage evidence and provider conflicts into actionable
    classifications.

    This layer does not invent encounter requirements, resolve ESO
    mechanics, or recommend specific roster changes. It interprets the
    already-resolved evidence conservatively.

    Resilience is supplied as explicit evidence by the caller. This class
    does not infer resilience from provider count alone.
    """

    def classify(
        self,
        *,
        effect_name: str,
        required_provider_count: int,
        providers: tuple[str, ...],
        satisfying_providers: tuple[str, ...],
        redundant_providers: tuple[str, ...] = (),
        resilient_providers: tuple[str, ...] = (),
        conflicting_providers: tuple[str, ...] = (),
        evidence_sufficient: bool = True,
    ) -> CoverageClassificationResult:
        """
        Classify one capability requirement from already-resolved evidence.
        """

        if required_provider_count < 1:
            raise ValueError(
                "required_provider_count must be at least 1."
            )

        valid_provider_count = len(satisfying_providers)

        if conflicting_providers:
            return CoverageClassificationResult(
                effect_name=effect_name,
                classification=CoverageClassification.CONFLICT,
                required_provider_count=required_provider_count,
                valid_provider_count=valid_provider_count,
                providers=providers,
                conflicting_providers=conflicting_providers,
                explanation=(
                    f"{effect_name} has providers that belong to an "
                    "explicitly conflicting exclusivity group."
                ),
            )

        if not evidence_sufficient:
            return CoverageClassificationResult(
                effect_name=effect_name,
                classification=CoverageClassification.UNKNOWN,
                required_provider_count=required_provider_count,
                valid_provider_count=valid_provider_count,
                providers=providers,
                resilient_providers=resilient_providers,
                explanation=(
                    f"The available evidence is insufficient to safely "
                    f"classify {effect_name}."
                ),
            )

        if valid_provider_count == 0:
            if providers:
                return CoverageClassificationResult(
                    effect_name=effect_name,
                    classification=CoverageClassification.INSUFFICIENT,
                    required_provider_count=required_provider_count,
                    valid_provider_count=0,
                    providers=providers,
                    explanation=(
                        f"{effect_name} has providers, but none satisfy "
                        "the requirement."
                    ),
                )

            return CoverageClassificationResult(
                effect_name=effect_name,
                classification=CoverageClassification.MISSING,
                required_provider_count=required_provider_count,
                valid_provider_count=0,
                providers=(),
                explanation=(
                    f"No provider can currently satisfy {effect_name}."
                ),
            )

        if valid_provider_count < required_provider_count:
            return CoverageClassificationResult(
                effect_name=effect_name,
                classification=CoverageClassification.INSUFFICIENT,
                required_provider_count=required_provider_count,
                valid_provider_count=valid_provider_count,
                providers=providers,
                explanation=(
                    f"{effect_name} requires "
                    f"{required_provider_count} valid provider(s), "
                    f"but only {valid_provider_count} qualify."
                ),
            )

        if resilient_providers:
            return CoverageClassificationResult(
                effect_name=effect_name,
                classification=CoverageClassification.RESILIENT,
                required_provider_count=required_provider_count,
                valid_provider_count=valid_provider_count,
                providers=providers,
                resilient_providers=resilient_providers,
                explanation=(
                    f"{effect_name} is satisfied, with "
                    f"{len(resilient_providers)} additional provider(s) "
                    "providing independent backup coverage."
                ),
            )

        if redundant_providers:
            return CoverageClassificationResult(
                effect_name=effect_name,
                classification=CoverageClassification.REDUNDANT,
                required_provider_count=required_provider_count,
                valid_provider_count=valid_provider_count,
                providers=providers,
                redundant_providers=redundant_providers,
                explanation=(
                    f"{effect_name} is satisfied, with "
                    f"{len(redundant_providers)} additional provider(s) "
                    "beyond the stated requirement."
                ),
            )

        return CoverageClassificationResult(
            effect_name=effect_name,
            classification=CoverageClassification.COVERED,
            required_provider_count=required_provider_count,
            valid_provider_count=valid_provider_count,
            providers=providers,
            explanation=(
                f"{effect_name} has sufficient valid provider coverage."
            ),
        )