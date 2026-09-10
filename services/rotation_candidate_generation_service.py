from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from minmax.demand_action_claim_duration_scheduler import DemandActionClaim
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationPlan
from minmax.rotation_wait_decision import PrematureRecastDecisionProvider
from services.rotation_duration_refinement_service import RotationDurationRefinementService


RotationCandidateWaitDecisionFactory = Callable[
    [],
    PrematureRecastDecisionProvider | None,
]


@dataclass(frozen=True)
class RotationRefreshLeadCandidateOption:
    """One caller-proven early-refresh policy variant.

    The generator never invents encounter strategy. Each option is an explicit
    set of already-validated semantic permissions supplied by a caller or sourced
    strategy layer. The empty baseline remains a separate generated candidate.
    """

    option_id: str
    refresh_leads: tuple[DemandRefreshLead, ...] = ()

    def __post_init__(self) -> None:
        option_id = str(self.option_id or "").strip()
        if not option_id:
            raise ValueError("rotation candidate option_id is required")
        object.__setattr__(self, "option_id", option_id)
        object.__setattr__(self, "refresh_leads", tuple(self.refresh_leads))


@dataclass(frozen=True)
class GeneratedRotationCandidate:
    candidate_id: str
    plan: RotationPlan
    refresh_leads: tuple[DemandRefreshLead, ...]
    action_claims: tuple[DemandActionClaim, ...] = ()


class _RefinementService(Protocol):
    def refine(
        self,
        plan: RotationPlan,
        *,
        priorities: AbilityPriorityList | None = None,
        wait_decision: PrematureRecastDecisionProvider | None = None,
        demands: tuple[RotationDemandWindow, ...] = (),
        demand_refresh_leads: tuple[DemandRefreshLead, ...] = (),
        demand_action_claims: tuple[DemandActionClaim, ...] = (),
    ): ...


class RotationCandidateGenerationService:
    """Generate deterministic rotation-plan variants from explicit policy options.

    Candidate generation and candidate judgment are intentionally separate.
    This service does not score, rank, or decide whether an option is good. It
    produces a baseline and caller-supplied schedule variants through the existing
    duration-refinement path so downstream scorecard/ranking services can compare
    the resulting whole plans under hard obligations.

    Stateful wait-decision providers must not leak runtime trigger state from one
    candidate into another. Callers with a stateful provider therefore supply
    ``wait_decision_factory`` so every candidate receives a fresh instance. The
    legacy ``wait_decision`` argument remains supported for stateless providers.

    ``generate_policy`` exposes the same canonical refinement path for one explicit
    candidate policy. Recovery fixed-point adapters use it to regenerate one policy
    repeatedly without generating unrelated siblings on every iteration. Explicit
    demand action claims are also preserved here so encounter-owned mechanic casts
    can become executable candidate actions instead of stopping at obligation data.
    Family-level ``action_claims`` are shared hard encounter obligations and are
    therefore applied identically to the baseline and every generated refresh-lead
    sibling. Demand action claims and caller-proven refresh leads may coexist in one
    policy; their deterministic precedence is owned by the canonical duration refiner.
    """

    DEFAULT_MAX_CANDIDATES = 32

    def __init__(
        self,
        refinement_service: _RefinementService | None = None,
        *,
        max_candidates: int = DEFAULT_MAX_CANDIDATES,
    ) -> None:
        if int(max_candidates) < 1:
            raise ValueError("rotation candidate max_candidates must be positive")
        self.refinement_service = refinement_service or RotationDurationRefinementService()
        self.max_candidates = int(max_candidates)

    def generate(
        self,
        *,
        seed_plan: RotationPlan,
        priorities: AbilityPriorityList,
        demands: tuple[RotationDemandWindow, ...] = (),
        options: tuple[RotationRefreshLeadCandidateOption, ...] = (),
        action_claims: tuple[DemandActionClaim, ...] = (),
        wait_decision: PrematureRecastDecisionProvider | None = None,
        wait_decision_factory: RotationCandidateWaitDecisionFactory | None = None,
        baseline_id: str = "baseline",
    ) -> tuple[GeneratedRotationCandidate, ...]:
        self._validate_wait_decision_inputs(
            wait_decision=wait_decision,
            wait_decision_factory=wait_decision_factory,
        )

        baseline = str(baseline_id or "").strip()
        if not baseline:
            raise ValueError("rotation candidate baseline_id is required")

        canonical_claims = self._canonical_claims(tuple(action_claims))
        normalized_options = self._dedupe_options(tuple(options))
        candidate_count = 1 + len(normalized_options)
        if candidate_count > self.max_candidates:
            raise ValueError(
                "rotation candidate family exceeds explicit limit: "
                f"{candidate_count} > {self.max_candidates}"
            )

        candidate_ids = {baseline.casefold()}
        for option in normalized_options:
            key = option.option_id.casefold()
            if key in candidate_ids:
                raise ValueError(f"duplicate rotation candidate id: {option.option_id}")
            candidate_ids.add(key)

        candidates = [
            self.generate_policy(
                candidate_id=baseline,
                seed_plan=seed_plan,
                priorities=priorities,
                demands=tuple(demands),
                refresh_leads=(),
                action_claims=canonical_claims,
                wait_decision=wait_decision,
                wait_decision_factory=wait_decision_factory,
            )
        ]
        for option in normalized_options:
            candidates.append(
                self.generate_policy(
                    candidate_id=option.option_id,
                    seed_plan=seed_plan,
                    priorities=priorities,
                    demands=tuple(demands),
                    refresh_leads=option.refresh_leads,
                    action_claims=canonical_claims,
                    wait_decision=wait_decision,
                    wait_decision_factory=wait_decision_factory,
                )
            )
        return tuple(candidates)

    def generate_policy(
        self,
        *,
        candidate_id: str,
        seed_plan: RotationPlan,
        priorities: AbilityPriorityList,
        demands: tuple[RotationDemandWindow, ...] = (),
        refresh_leads: tuple[DemandRefreshLead, ...] = (),
        action_claims: tuple[DemandActionClaim, ...] = (),
        wait_decision: PrematureRecastDecisionProvider | None = None,
        wait_decision_factory: RotationCandidateWaitDecisionFactory | None = None,
    ) -> GeneratedRotationCandidate:
        """Generate one explicit candidate policy through the canonical refiner."""

        self._validate_wait_decision_inputs(
            wait_decision=wait_decision,
            wait_decision_factory=wait_decision_factory,
        )
        resolved_id = str(candidate_id or "").strip()
        if not resolved_id:
            raise ValueError("rotation candidate candidate_id is required")
        canonical_leads = self._canonical_leads(tuple(refresh_leads))
        canonical_claims = self._canonical_claims(tuple(action_claims))
        return self._generate_one(
            candidate_id=resolved_id,
            seed_plan=seed_plan,
            priorities=priorities,
            demands=tuple(demands),
            refresh_leads=canonical_leads,
            action_claims=canonical_claims,
            wait_decision=self._candidate_wait_decision(
                wait_decision=wait_decision,
                wait_decision_factory=wait_decision_factory,
            ),
        )

    def _generate_one(
        self,
        *,
        candidate_id: str,
        seed_plan: RotationPlan,
        priorities: AbilityPriorityList,
        demands: tuple[RotationDemandWindow, ...],
        refresh_leads: tuple[DemandRefreshLead, ...],
        action_claims: tuple[DemandActionClaim, ...],
        wait_decision: PrematureRecastDecisionProvider | None,
    ) -> GeneratedRotationCandidate:
        refinement = self.refinement_service.refine(
            seed_plan,
            priorities=priorities,
            wait_decision=wait_decision,
            demands=demands,
            demand_refresh_leads=refresh_leads,
            demand_action_claims=action_claims,
        )
        return GeneratedRotationCandidate(
            candidate_id=candidate_id,
            plan=refinement.plan,
            refresh_leads=refresh_leads,
            action_claims=action_claims,
        )

    @staticmethod
    def _validate_wait_decision_inputs(
        *,
        wait_decision: PrematureRecastDecisionProvider | None,
        wait_decision_factory: RotationCandidateWaitDecisionFactory | None,
    ) -> None:
        if wait_decision is not None and wait_decision_factory is not None:
            raise ValueError(
                "rotation candidate generation accepts either wait_decision or "
                "wait_decision_factory, not both"
            )

    @staticmethod
    def _candidate_wait_decision(
        *,
        wait_decision: PrematureRecastDecisionProvider | None,
        wait_decision_factory: RotationCandidateWaitDecisionFactory | None,
    ) -> PrematureRecastDecisionProvider | None:
        if wait_decision_factory is not None:
            return wait_decision_factory()
        return wait_decision

    @classmethod
    def _dedupe_options(
        cls,
        options: tuple[RotationRefreshLeadCandidateOption, ...],
    ) -> tuple[RotationRefreshLeadCandidateOption, ...]:
        """Remove semantically duplicate lead sets while preserving first intent.

        Candidate IDs are presentation/provenance labels. Two differently named
        options that produce the same exact refresh-lead policy are still one
        semantic schedule candidate, so the first supplied option wins. The empty
        lead set is already represented by the baseline and is therefore omitted.
        """

        seen: set[tuple[tuple[str, str, str, float], ...]] = {()}
        result: list[RotationRefreshLeadCandidateOption] = []
        for option in options:
            leads = cls._canonical_leads(option.refresh_leads)
            key = cls._lead_key(leads)
            if key in seen:
                continue
            seen.add(key)
            result.append(
                RotationRefreshLeadCandidateOption(
                    option_id=option.option_id,
                    refresh_leads=leads,
                )
            )
        return tuple(result)

    @staticmethod
    def _canonical_leads(
        leads: tuple[DemandRefreshLead, ...],
    ) -> tuple[DemandRefreshLead, ...]:
        ordered = sorted(
            tuple(leads),
            key=lambda item: (
                item.demand_name.casefold(),
                item.bar,
                item.skill_name.casefold(),
                item.lead_seconds,
            ),
        )
        seen_targets: set[tuple[str, str, str]] = set()
        for item in ordered:
            target = (item.demand_name, item.bar, item.skill_name.casefold())
            if target in seen_targets:
                raise ValueError(
                    "rotation candidate contains duplicate refresh-lead target: "
                    f"{item.demand_name}: {item.skill_name} on {item.bar} bar"
                )
            seen_targets.add(target)
        return tuple(ordered)

    @staticmethod
    def _canonical_claims(
        claims: tuple[DemandActionClaim, ...],
    ) -> tuple[DemandActionClaim, ...]:
        ordered = sorted(
            tuple(claims),
            key=lambda item: (
                item.demand_name.casefold(),
                item.bar,
                item.skill_name.casefold(),
            ),
        )
        seen_targets: set[tuple[str, str, str]] = set()
        for item in ordered:
            target = (item.demand_name.casefold(), item.bar, item.skill_name.casefold())
            if target in seen_targets:
                raise ValueError(
                    "rotation candidate contains duplicate demand action claim target: "
                    f"{item.demand_name}: {item.skill_name} on {item.bar} bar"
                )
            seen_targets.add(target)
        return tuple(ordered)

    @staticmethod
    def _lead_key(
        leads: tuple[DemandRefreshLead, ...],
    ) -> tuple[tuple[str, str, str, float], ...]:
        return tuple(
            (
                item.demand_name.casefold(),
                item.bar,
                item.skill_name.casefold(),
                float(item.lead_seconds),
            )
            for item in leads
        )


__all__ = [
    "GeneratedRotationCandidate",
    "RotationCandidateGenerationService",
    "RotationCandidateWaitDecisionFactory",
    "RotationRefreshLeadCandidateOption",
]
