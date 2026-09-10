from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateRoleHardObligationEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_multi_demand_role_output_service import (
    RotationCandidateHealerMultiDemandOutput,
    RotationCandidateHealerMultiDemandRoleOutputService,
)


class RotationHealerDemandCriterionSourceKind(str, Enum):
    """Authority level for one numeric healer encounter criterion."""

    VERIFIED_ENCOUNTER_EVIDENCE = "verified_encounter_evidence"
    CALLER_ASSUMPTION = "caller_assumption"


@dataclass(frozen=True)
class RotationHealerDemandCriterion:
    """Explicit minimum modeled healer output for one named demand window.

    The threshold is expressed in the same pre-recipient, pre-overheal modeled
    healing-per-demand-second units used by healer role-output evidence. It is not
    observed HPS and does not independently prove survival.

    A criterion may be authoritative encounter evidence or an explicit caller
    assumption. Only verified encounter evidence is eligible to become a hard
    encounter obligation; assumptions remain diagnostic until independently
    verified.
    """

    demand_name: str
    minimum_modeled_healing_per_demand_second: float
    source_kind: RotationHealerDemandCriterionSourceKind
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        name = str(self.demand_name or "").strip()
        if not name:
            raise ValueError("healer demand criterion requires demand_name")
        object.__setattr__(self, "demand_name", name)

        value = float(self.minimum_modeled_healing_per_demand_second)
        if not isfinite(value) or value < 0.0:
            raise ValueError(
                "healer demand criterion minimum must be finite and non-negative"
            )
        object.__setattr__(self, "minimum_modeled_healing_per_demand_second", value)

        if not isinstance(self.source_kind, RotationHealerDemandCriterionSourceKind):
            object.__setattr__(
                self,
                "source_kind",
                RotationHealerDemandCriterionSourceKind(str(self.source_kind)),
            )

        provenance = tuple(
            dict.fromkeys(str(item).strip() for item in self.provenance if str(item).strip())
        )
        if not provenance:
            raise ValueError("healer demand criterion requires provenance")
        object.__setattr__(self, "provenance", provenance)

    @property
    def authoritative(self) -> bool:
        return (
            self.source_kind
            is RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE
        )


@dataclass(frozen=True)
class RotationHealerDemandCriterionAssessment:
    criterion: RotationHealerDemandCriterion
    modeled_healing_per_demand_second: float | None
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.modeled_healing_per_demand_second is not None and not self.unresolved

    @property
    def meets_threshold(self) -> bool | None:
        if not self.resolved:
            return None
        assert self.modeled_healing_per_demand_second is not None
        return (
            self.modeled_healing_per_demand_second
            >= self.criterion.minimum_modeled_healing_per_demand_second
        )

    @property
    def hard_obligation_satisfied(self) -> bool | None:
        """Return hard-gate state only for authoritative encounter evidence."""
        if not self.criterion.authoritative:
            return None
        return self.meets_threshold


@dataclass(frozen=True)
class RotationHealerDemandCriteriaAssessment:
    candidate_id: str
    assessments: tuple[RotationHealerDemandCriterionAssessment, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def failed_authoritative(self) -> tuple[RotationHealerDemandCriterionAssessment, ...]:
        return tuple(
            item
            for item in self.assessments
            if item.criterion.authoritative and item.hard_obligation_satisfied is False
        )

    @property
    def unresolved_authoritative(self) -> tuple[RotationHealerDemandCriterionAssessment, ...]:
        return tuple(
            item
            for item in self.assessments
            if item.criterion.authoritative and item.hard_obligation_satisfied is None
        )

    @property
    def hard_obligations_satisfied(self) -> bool:
        return not self.failed_authoritative and not self.unresolved_authoritative


class RotationHealerDemandCriteriaService:
    """Assess explicit encounter healer criteria against canonical window output.

    This service owns no healing math and invents no thresholds. It only joins
    caller-supplied, provenance-bearing criteria to already-modeled demand-window
    output. Missing candidate evidence fails closed for authoritative criteria.
    Caller assumptions are preserved for diagnostics but never become hard gates.
    """

    def assess(
        self,
        *,
        output: RotationCandidateHealerMultiDemandOutput,
        criteria: tuple[RotationHealerDemandCriterion, ...],
    ) -> RotationHealerDemandCriteriaAssessment:
        criteria = tuple(criteria)
        seen: set[str] = set()
        for criterion in criteria:
            key = criterion.demand_name.casefold()
            if key in seen:
                raise ValueError(
                    f"duplicate healer demand criterion: {criterion.demand_name!r}"
                )
            seen.add(key)

        windows = {item.demand.name.casefold(): item for item in output.windows}
        assessments: list[RotationHealerDemandCriterionAssessment] = []
        unresolved: list[str] = list(output.unresolved)

        for criterion in criteria:
            window = windows.get(criterion.demand_name.casefold())
            if window is None:
                message = (
                    f"{criterion.demand_name}: candidate healing-window output unavailable"
                )
                assessments.append(
                    RotationHealerDemandCriterionAssessment(
                        criterion=criterion,
                        modeled_healing_per_demand_second=None,
                        unresolved=(message,),
                    )
                )
                unresolved.append(message)
                continue

            window_unresolved = tuple(window.unresolved)
            value = window.modeled_healing_per_demand_second
            if window_unresolved or value is None:
                messages = tuple(
                    f"{criterion.demand_name}: {message}" for message in window_unresolved
                ) or (
                    f"{criterion.demand_name}: modeled healer output unresolved",
                )
                assessments.append(
                    RotationHealerDemandCriterionAssessment(
                        criterion=criterion,
                        modeled_healing_per_demand_second=None,
                        unresolved=messages,
                    )
                )
                unresolved.extend(messages)
                continue

            assessments.append(
                RotationHealerDemandCriterionAssessment(
                    criterion=criterion,
                    modeled_healing_per_demand_second=float(value),
                )
            )

        return RotationHealerDemandCriteriaAssessment(
            candidate_id=output.candidate_id,
            assessments=tuple(assessments),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


class RotationCandidateHealerCriteriaHardObligationService:
    """Expose verified healer demand criteria through the generic role hard gate.

    Caller assumptions remain outside this hard-obligation channel. A resolved
    verified threshold miss returns ``False``; unresolved verified evidence returns
    ``None`` so recommendation fails closed; otherwise the role hard gate passes.
    """

    def __init__(
        self,
        *,
        multi_demand_output_service: RotationCandidateHealerMultiDemandRoleOutputService,
        criteria: tuple[RotationHealerDemandCriterion, ...],
        criteria_service: RotationHealerDemandCriteriaService | None = None,
    ) -> None:
        self.multi_demand_output_service = multi_demand_output_service
        self.criteria = tuple(criteria)
        self.criteria_service = criteria_service or RotationHealerDemandCriteriaService()

    def evaluate_plan(
        self,
        candidate: GeneratedRotationCandidate,
    ) -> RotationCandidateRoleHardObligationEvidence:
        output = self.multi_demand_output_service.evaluate_windows(candidate)
        assessment = self.criteria_service.assess(
            output=output,
            criteria=self.criteria,
        )

        if assessment.candidate_id.casefold() != candidate.candidate_id.casefold():
            raise ValueError(
                "healer criteria assessment candidate mismatch: "
                f"expected {candidate.candidate_id!r}, got {assessment.candidate_id!r}"
            )

        reasons: list[str] = []
        for item in assessment.failed_authoritative:
            observed = item.modeled_healing_per_demand_second
            required = item.criterion.minimum_modeled_healing_per_demand_second
            provenance = "; ".join(item.criterion.provenance)
            reasons.append(
                f"verified healer criterion failed for {item.criterion.demand_name!r}: "
                f"modeled {observed:g} < required {required:g}; provenance: {provenance}"
            )

        for item in assessment.unresolved_authoritative:
            detail = "; ".join(item.unresolved) or "authoritative criterion unresolved"
            provenance = "; ".join(item.criterion.provenance)
            reasons.append(
                f"verified healer criterion unresolved for {item.criterion.demand_name!r}: "
                f"{detail}; provenance: {provenance}"
            )

        if assessment.unresolved_authoritative:
            satisfied: bool | None = None
        elif assessment.failed_authoritative:
            satisfied = False
        else:
            satisfied = True

        return RotationCandidateRoleHardObligationEvidence(
            candidate_id=candidate.candidate_id,
            satisfied=satisfied,
            reasons=tuple(reasons),
        )


__all__ = [
    "RotationCandidateHealerCriteriaHardObligationService",
    "RotationHealerDemandCriterion",
    "RotationHealerDemandCriterionAssessment",
    "RotationHealerDemandCriterionSourceKind",
    "RotationHealerDemandCriteriaAssessment",
    "RotationHealerDemandCriteriaService",
]
