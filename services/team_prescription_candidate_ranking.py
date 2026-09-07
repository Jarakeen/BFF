from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from minmax.build_candidate_comparison import BuildCandidateComparison

from .named_buff_resolution_service import NamedBuffContribution
from .team_provider_coverage_service import (
    TeamProviderCoverageProfile,
    TeamProviderCoverageService,
)
from .team_provider_marginal_value_service import (
    TeamProviderMarginalValue,
    TeamProviderMarginalValueService,
)
from .team_role_autofill import normalize_team_role, slot_role_family
from .team_prescription_candidate_source import PrescribedOpenSlotCandidateEvidence


@dataclass(frozen=True)
class PrescribedSlotCandidateEvidence:
    """One comparable candidate evidence shape for a prescribed roster slot."""

    comparison: BuildCandidateComparison | None = None
    open_slot: PrescribedOpenSlotCandidateEvidence | None = None
    provider_requirement_ids: tuple[str, ...] = ()
    provider_effects: tuple[NamedBuffContribution, ...] = ()
    provider_coverage_profiles: tuple[TeamProviderCoverageProfile, ...] = ()

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
        object.__setattr__(self, "provider_effects", tuple(self.provider_effects))
        object.__setattr__(
            self,
            "provider_coverage_profiles",
            tuple(self.provider_coverage_profiles),
        )

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
    provider_marginal_values: tuple[tuple[str, TeamProviderMarginalValue], ...] = ()


def _normalized_provider_key(value: object) -> str:
    return str(value or "").strip().casefold()


def rank_prescribed_slot_candidates(
    *,
    slot_name: str,
    required_provider_requirement_ids: tuple[str, ...],
    candidates: tuple[PrescribedSlotCandidateEvidence, ...],
    existing_team_effects: tuple[NamedBuffContribution, ...] = (),
    provider_required_recipients_by_id: dict[str, int] | None = None,
) -> PrescribedSlotCandidateRanking:
    """Rank one prescribed roster slot without weakening Phase 12 constraints.

    Phase 12 remains authoritative when an anchored-player build comparison is
    supplied. Open chairs use absolute canonical objective evidence because they have
    no honest baseline. This layer adds roster-scale role/provider gates and refuses
    to compare unlike score types.

    Named provider effects are deliberately not added to damage/healing/tanking
    objective numbers because those units are incomparable. When otherwise equally
    supported candidates tie on the canonical objective, however, the candidate that
    adds more distinct reviewed named effects beyond the current team may break that
    tie. If marginal provider evidence is also tied, the slot remains unresolved.

    Provider identity alone is not enough when an encounter requirement declares a
    recipient count. The candidate must also carry coverage profiles proving that
    its provider can reach the required number of recipients within the modeled
    refresh/application cycle. Requirements without a recipient count preserve the
    legacy provider-ID behavior.
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
    required_recipients = {
        _normalized_provider_key(provider_id): int(count)
        for provider_id, count in (provider_required_recipients_by_id or {}).items()
        if _normalized_provider_key(provider_id)
    }
    if any(count < 0 for count in required_recipients.values()):
        raise ValueError("provider required recipient counts cannot be negative")

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

        profiles_by_key: dict[str, list[TeamProviderCoverageProfile]] = {}
        for profile in evidence.provider_coverage_profiles:
            profiles_by_key.setdefault(
                _normalized_provider_key(profile.provider_key),
                [],
            ).append(profile)
        for requirement_id in required_provider_ids:
            if requirement_id in missing_provider_ids:
                continue
            recipient_count = required_recipients.get(_normalized_provider_key(requirement_id))
            if recipient_count is None:
                continue
            profiles = tuple(profiles_by_key.get(_normalized_provider_key(requirement_id), ()))
            if not profiles:
                reasons.append(
                    f"required provider coverage is unproven for {requirement_id}: "
                    f"no coverage profile for {recipient_count} intended recipients"
                )
                continue
            coverage = TeamProviderCoverageService.combine(
                profiles,
                required_recipients=recipient_count,
            )
            if not coverage.fully_covered:
                reasons.append(
                    f"insufficient provider coverage for {requirement_id}: "
                    f"covers {coverage.covered_recipients}/{recipient_count} intended recipients"
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
    marginal_values: tuple[tuple[str, TeamProviderMarginalValue], ...] = ()
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
            evaluated = tuple(
                (
                    evidence.candidate_id,
                    TeamProviderMarginalValueService.evaluate(
                        existing_team_effects=existing_team_effects,
                        candidate_effects=evidence.provider_effects,
                    ),
                )
                for evidence in tied
            )
            marginal_values = evaluated
            counts = {
                candidate_id: value.new_named_effect_count
                for candidate_id, value in evaluated
            }
            best_count = max(counts.values(), default=0)
            marginal_winners = tuple(
                evidence
                for evidence in tied
                if counts.get(evidence.candidate_id, 0) == best_count
            )
            if best_count > 0 and len(marginal_winners) == 1:
                recommended = marginal_winners[0]
            else:
                recommended = None
                unresolved = (
                    f"{normalized_slot}: {len(tied)} equally supported top candidates remain; "
                    "marginal team-provider evidence does not uniquely separate them",
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
        provider_marginal_values=marginal_values,
    )
