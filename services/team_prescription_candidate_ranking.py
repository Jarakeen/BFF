from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from minmax.build_candidate_comparison import BuildCandidateComparison

from .team_role_autofill import normalize_team_role, slot_role_family
from .team_prescription_candidate_source import PrescribedOpenSlotCandidateEvidence


@dataclass(frozen=True)
class PrescribedSlotCandidateEvidence:
    """One comparable candidate evidence shape for a prescribed roster slot."""

    comparison: BuildCandidateComparison | None = None
    open_slot: PrescribedOpenSlotCandidateEvidence | None = None
    provider_requirement_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (self.comparison is None) == (self.open_slot is None):
            raise ValueError(
                "prescribed slot evidence requires exactly one of comparison or open_slot"
            )
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

    @property
    def candidate_id(self) -> str:
        if self.comparison is not None:
            return self.comparison.candidate.candidate_id
        assert self.open_slot is not None
        return self.open_slot.candidate.candidate_id

    @property
    def candidate_build(self):
        if self.comparison is not None:
            return self.comparison.candidate.candidate_build
        assert self.open_slot is not None
        return self.open_slot.candidate.candidate_build

    @property
    def is_rankable(self) -> bool:
        if self.comparison is not None:
            return self.comparison.is_rankable
        assert self.open_slot is not None
        return self.open_slot.measurement.is_rankable

    @property
    def is_preferred(self) -> bool:
        if self.comparison is not None:
            return self.comparison.is_preferred
        return self.is_rankable

    @property
    def ranking_value(self) -> float | None:
        if self.comparison is not None:
            return self.comparison.delta
        assert self.open_slot is not None
        return self.open_slot.measurement.value

    @property
    def evidence_kind(self) -> str:
        return "baseline comparison" if self.comparison is not None else "absolute objective"

    @property
    def preference_class(self) -> tuple[bool, bool]:
        if self.comparison is not None:
            return (
                self.comparison.is_constraint_repair,
                self.comparison.is_improvement,
            )
        return (False, True)


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

    Phase 12 remains authoritative when an anchored-player build comparison is
    supplied. Open chairs use absolute canonical objective evidence because they have
    no honest baseline. This layer adds the roster-scale role/provider gates and
    refuses to compare the two unlike score types. Equivalent top candidates remain
    unresolved rather than using identifier order as stronger gameplay evidence.
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
        candidate_id = evidence.candidate_id
        reasons: list[str] = []

        candidate_role = normalize_team_role(evidence.candidate_build.Role)
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

        if not evidence.is_rankable:
            reasons.append(
                "Phase 12 comparison is not rankable"
                if evidence.comparison is not None
                else "absolute objective is not rankable"
            )

        if reasons:
            rejected.append(
                PrescribedSlotCandidateRejection(
                    candidate_id=candidate_id,
                    reasons=tuple(reasons),
                )
            )
            continue

        eligible.append(evidence)

    kinds = {evidence.evidence_kind for evidence in eligible}
    if len(kinds) > 1:
        return PrescribedSlotCandidateRanking(
            slot_name=normalized_slot,
            required_role=required_role,
            required_provider_requirement_ids=required_provider_ids,
            eligible=tuple(eligible),
            rejected=tuple(rejected),
            recommended=None,
            recommended_ties=(),
            unresolved=(
                f"{normalized_slot}: baseline deltas and absolute open-slot objective "
                "values cannot be ranked together",
            ),
        )

    ranked = tuple(
        sorted(
            (evidence for evidence in eligible if evidence.is_preferred),
            key=lambda evidence: (
                -float(evidence.ranking_value or 0.0),
                evidence.candidate_id.casefold(),
                evidence.candidate_id,
            ),
        )
    )
    recommended = ranked[0] if ranked else None

    recommended_ties: tuple[PrescribedSlotCandidateEvidence, ...] = ()
    unresolved: tuple[str, ...] = ()
    if recommended is not None and recommended.ranking_value is not None:
        top_value = float(recommended.ranking_value)
        tied = tuple(
            evidence
            for evidence in eligible
            if evidence.is_preferred
            and evidence.ranking_value is not None
            and evidence.preference_class == recommended.preference_class
            and isclose(
                float(evidence.ranking_value),
                top_value,
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
