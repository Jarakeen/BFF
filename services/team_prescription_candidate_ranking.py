from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from minmax.build_candidate_comparison import BuildCandidateComparison
from minmax.build_candidate_evaluator import rank_candidate_comparisons

from .team_role_autofill import normalize_team_role, slot_role_family


@dataclass(frozen=True)
class PrescribedSlotCandidateEvidence:
    """One Phase 12 candidate plus team-scale evidence for one roster slot."""

    comparison: BuildCandidateComparison
    provider_requirement_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        normalized = tuple(
            dict.fromkeys(
                value
                for value in (
                    str(item or "").strip() for item in self.provider_requirement_ids
                )
                if value
            )
        )
        object.__setattr__(self, "provider_requirement_ids", normalized)


@dataclass(frozen=True)
class PrescribedSlotCandidateRejection:
    candidate_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PrescribedSlotCandidateRanking:
    slot_name: str
    required_role: str
    required_provider_requirement_ids: tuple[str, ...]
    eligible: tuple[PrescribedSlotCandidateEvidence, ...]
    rejected: tuple[PrescribedSlotCandidateRejection, ...]
    recommended: PrescribedSlotCandidateEvidence | None
    recommended_ties: tuple[PrescribedSlotCandidateEvidence, ...]
    unresolved: tuple[str, ...] = ()


def rank_prescribed_slot_candidates(
    *,
    slot_name: str,
    required_provider_requirement_ids: tuple[str, ...],
    candidates: tuple[PrescribedSlotCandidateEvidence, ...],
) -> PrescribedSlotCandidateRanking:
    """Rank one prescribed roster slot without weakening Phase 12 constraints.

    Phase 12 remains authoritative for whether a build comparison is rankable.
    This layer adds only roster-scale gates: exact role-family compatibility and
    explicit provider requirements allocated to this slot. Objective ordering is
    delegated back to Phase 12. Equivalent top candidates remain unresolved rather
    than using identifier order as stronger gameplay evidence.
    """

    normalized_slot = str(slot_name or "").strip()
    if not normalized_slot:
        raise ValueError("prescribed slot candidate ranking requires a slot name")
    required_role = slot_role_family(normalized_slot)
    required_provider_ids = tuple(
        dict.fromkeys(
            value
            for value in (
                str(item or "").strip() for item in required_provider_requirement_ids
            )
            if value
        )
    )

    eligible: list[PrescribedSlotCandidateEvidence] = []
    rejected: list[PrescribedSlotCandidateRejection] = []

    for evidence in candidates:
        comparison = evidence.comparison
        candidate_id = comparison.candidate.candidate_id
        reasons: list[str] = []

        candidate_role = normalize_team_role(comparison.candidate.candidate_build.Role)
        if candidate_role != required_role:
            reasons.append(
                f"role mismatch: slot requires {required_role}, candidate role is "
                f"{candidate_role or 'unresolved'}"
            )

        missing_provider_ids = tuple(
            requirement_id
            for requirement_id in required_provider_ids
            if requirement_id not in evidence.provider_requirement_ids
        )
        if missing_provider_ids:
            reasons.append(
                "missing required provider evidence: " + ", ".join(missing_provider_ids)
            )

        if not comparison.is_rankable:
            reasons.append("Phase 12 comparison is not rankable")

        if reasons:
            rejected.append(
                PrescribedSlotCandidateRejection(
                    candidate_id=candidate_id,
                    reasons=tuple(reasons),
                )
            )
            continue

        eligible.append(evidence)

    ranking = rank_candidate_comparisons(
        tuple(evidence.comparison for evidence in eligible)
    )
    evidence_by_id = {
        evidence.comparison.candidate.candidate_id: evidence for evidence in eligible
    }
    recommended_comparison = ranking.recommended
    recommended = (
        evidence_by_id[recommended_comparison.candidate.candidate_id]
        if recommended_comparison is not None
        else None
    )

    recommended_ties: tuple[PrescribedSlotCandidateEvidence, ...] = ()
    unresolved: tuple[str, ...] = ()
    if recommended is not None and recommended.comparison.delta is not None:
        top_delta = float(recommended.comparison.delta)
        tied = tuple(
            evidence
            for evidence in eligible
            if evidence.comparison.is_preferred
            and evidence.comparison.delta is not None
            and evidence.comparison.is_constraint_repair
            is recommended.comparison.is_constraint_repair
            and evidence.comparison.is_improvement
            is recommended.comparison.is_improvement
            and isclose(
                float(evidence.comparison.delta),
                top_delta,
                rel_tol=0.0,
                abs_tol=1e-9,
            )
        )
        recommended_ties = tied
        if len(tied) > 1:
            recommended = None
            unresolved = (
                f"{normalized_slot}: {len(tied)} equally supported top candidates remain; "
                "additional strategy evidence is required before prescribing one",
            )

    return PrescribedSlotCandidateRanking(
        slot_name=normalized_slot,
        required_role=required_role,
        required_provider_requirement_ids=required_provider_ids,
        eligible=tuple(eligible),
        rejected=tuple(rejected),
        recommended=recommended,
        recommended_ties=recommended_ties,
        unresolved=unresolved,
    )
