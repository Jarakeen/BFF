from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_plan_consequence_service import RotationResourceConsequenceKind


_RESOURCE_ORDER = {
    RotationResourceConsequenceKind.IMPROVED: 0,
    RotationResourceConsequenceKind.NEUTRAL: 1,
    RotationResourceConsequenceKind.MIXED: 2,
    RotationResourceConsequenceKind.WORSENED: 3,
}


class RotationCandidateTier(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True)
class RotationCandidateRankingInput:
    candidate_id: str
    scorecard: RotationCandidateScorecard

    def __post_init__(self) -> None:
        value = str(self.candidate_id or "").strip()
        if not value:
            raise ValueError("rotation ranking candidate_id must be non-empty")
        object.__setattr__(self, "candidate_id", value)


@dataclass(frozen=True)
class RotationCandidateRankingResult:
    candidate_id: str
    scorecard: RotationCandidateScorecard
    tier: RotationCandidateTier
    rank: int
    reasons: tuple[str, ...]


class RotationCandidateRankingService:
    """Rank candidate rotations with hard obligations before soft consequences.

    This is intentionally lexicographic rather than weighted. A candidate that
    misses an explicit demand action, required static support effect, runtime
    uptime floor, demand-entry resource reserve, encounter bar-availability rule,
    resolved action cooldown or occupancy rule, or incurs resource shortfall cannot
    outrank one that satisfies those supplied hard obligations merely because its
    softer resource numbers look prettier.

    Within the same eligibility tier, deterministic evidence ordering is used:
    fewer missing obligations, smaller reserve/runtime shortfalls, fewer
    candidate-specific unresolved items, then resource consequence. When canonical
    bar-sensitive maximum evidence exists, normalized minimum/ending resource
    fractions break soft resource ties before raw absolute deltas. Otherwise-equal
    resource outcomes prefer less recovery/restoration wasted against the active
    ceiling. Explicit bar-swap burden is used only as a final soft tie-break before
    the stable candidate-id fallback. Heavy-attack, total-action, light-attack, and
    potion burden are currently diagnostic only because extra actions may be
    required by sustain, encounter obligations, support maintenance, or explicit
    caller intent. Shared baseline or model limitations remain visible but do not
    count against one candidate specifically.
    """

    def rank(
        self,
        candidates: tuple[RotationCandidateRankingInput, ...],
    ) -> tuple[RotationCandidateRankingResult, ...]:
        seen: set[str] = set()
        for item in candidates:
            key = item.candidate_id.casefold()
            if key in seen:
                raise ValueError(f"duplicate rotation ranking candidate_id: {item.candidate_id!r}")
            seen.add(key)

        self._validate_uptime_objective(candidates)

        ordered = sorted(candidates, key=self._sort_key)
        return tuple(
            RotationCandidateRankingResult(
                candidate_id=item.candidate_id,
                scorecard=item.scorecard,
                tier=(
                    RotationCandidateTier.ELIGIBLE
                    if item.scorecard.supplied_obligations_satisfied
                    else RotationCandidateTier.INELIGIBLE
                ),
                rank=index + 1,
                reasons=self._reasons(item.scorecard),
            )
            for index, item in enumerate(ordered)
        )

    @classmethod
    def _sort_key(cls, item: RotationCandidateRankingInput) -> tuple[object, ...]:
        scorecard = item.scorecard
        consequence = scorecard.consequence
        missing_demand = len(scorecard.missing_demand_requirements)
        missing_effects = len(scorecard.missing_required_effects)
        bar_violations = len(scorecard.bar_availability_violations)
        cooldown_violations = len(getattr(scorecard, "cooldown_violations", ()))
        occupancy_violations = len(getattr(scorecard, "occupancy_violations", ()))
        failed_uptimes = scorecard.failed_runtime_uptime_assessments
        uptime_failure_count = len(failed_uptimes)
        uptime_evidence_missing = sum(
            1 for assessment in failed_uptimes if assessment.observed_uptime is None
        )
        uptime_shortfall = sum(
            assessment.shortfall or 0.0 for assessment in failed_uptimes
        )
        objective = scorecard.runtime_uptime_objective_assessment
        objective_evidence_missing = int(
            objective is not None and objective.observed_uptime is None
        )
        objective_uptime = (
            objective.observed_uptime
            if objective is not None and objective.observed_uptime is not None
            else 0.0
        )
        failed_reserves = scorecard.failed_reserve_assessments
        reserve_failure_count = len(failed_reserves)
        reserve_shortfall = sum(int(assessment.shortfall) for assessment in failed_reserves)
        hard_failure_count = (
            missing_demand
            + missing_effects
            + bar_violations
            + cooldown_violations
            + occupancy_violations
            + uptime_failure_count
            + reserve_failure_count
            + (1 if scorecard.candidate_shortfall > 0 else 0)
        )
        minimum_fraction_delta = consequence.minimum_resource_fraction_delta
        ending_fraction_delta = consequence.ending_resource_fraction_delta

        return (
            0 if scorecard.supplied_obligations_satisfied else 1,
            hard_failure_count,
            missing_demand,
            missing_effects,
            bar_violations,
            cooldown_violations,
            occupancy_violations,
            uptime_failure_count,
            uptime_evidence_missing,
            uptime_shortfall,
            reserve_failure_count,
            reserve_shortfall,
            int(scorecard.candidate_shortfall),
            len(scorecard.candidate_specific_unresolved),
            objective_evidence_missing,
            -objective_uptime,
            _RESOURCE_ORDER[consequence.resource_kind],
            -(minimum_fraction_delta if minimum_fraction_delta is not None else 0.0),
            -(ending_fraction_delta if ending_fraction_delta is not None else 0.0),
            -int(consequence.minimum_resource_delta),
            -int(consequence.ending_resource_delta),
            int(getattr(consequence, "candidate_wasted_restore", 0)),
            int(consequence.total_cost_delta),
            int(consequence.wait_delta),
            int(getattr(consequence, "candidate_bar_swaps", 0)),
            item.candidate_id.casefold(),
        )

    @staticmethod
    def _reasons(scorecard: RotationCandidateScorecard) -> tuple[str, ...]:
        reasons: list[str] = []
        if scorecard.missing_demand_requirements:
            reasons.append(
                f"missing {len(scorecard.missing_demand_requirements)} explicit demand requirement(s)"
            )
        if scorecard.missing_required_effects:
            reasons.append(
                "missing static required effect(s): "
                + ", ".join(scorecard.missing_required_effects)
            )
        if scorecard.bar_availability_violations:
            reasons.append(
                f"{len(scorecard.bar_availability_violations)} encounter bar-availability violation(s)"
            )
            for violation in scorecard.bar_availability_violations:
                action = violation.action_name or (
                    violation.action_kind.value if violation.action_kind is not None else "bar state"
                )
                reasons.append(
                    f"bar legality at {violation.time_seconds:g}s in {violation.window_name!r}: "
                    f"{action} -> {violation.reason}"
                )
        cooldown_violations = tuple(getattr(scorecard, "cooldown_violations", ()))
        if cooldown_violations:
            reasons.append(f"{len(cooldown_violations)} action cooldown violation(s)")
            for violation in cooldown_violations:
                requirement = violation.requirement
                scope = f" on {requirement.bar} bar" if requirement.bar else ""
                reasons.append(
                    f"cooldown legality for {requirement.action_name!r}{scope} at "
                    f"{violation.time_seconds:g}s: interval "
                    f"{violation.actual_interval_seconds:g}s, required "
                    f"{violation.required_interval_seconds:g}s"
                )
        occupancy_violations = tuple(getattr(scorecard, "occupancy_violations", ()))
        if occupancy_violations:
            reasons.append(f"{len(occupancy_violations)} action occupancy violation(s)")
            for violation in occupancy_violations:
                requirement = violation.requirement
                scope = f" on {requirement.bar} bar" if requirement.bar else ""
                blocked = violation.blocked_action_name or violation.blocked_action_kind.value
                reasons.append(
                    f"occupancy legality for {requirement.action_name!r}{scope} from "
                    f"{violation.occupying_time_seconds:g}s to "
                    f"{violation.occupying_until_seconds:g}s: "
                    f"{blocked!r} scheduled at {violation.blocked_time_seconds:g}s"
                )
        for assessment in scorecard.failed_runtime_uptime_assessments:
            requirement = assessment.requirement
            scope = f" on {requirement.bar} bar" if requirement.bar else ""
            if assessment.observed_uptime is None:
                reasons.append(
                    f"runtime uptime evidence missing for {requirement.skill_name!r}{scope}"
                )
            else:
                reasons.append(
                    f"runtime uptime below minimum for {requirement.skill_name!r}{scope}: "
                    f"observed {assessment.observed_uptime:.2%}, "
                    f"required {requirement.minimum_uptime:.2%}"
                )
        for assessment in scorecard.failed_reserve_assessments:
            available_fraction = assessment.available_fraction_before_start
            required_fraction = getattr(assessment, "required_fraction_before_start", None)
            shortfall_fraction = getattr(assessment, "shortfall_fraction", None)
            available_normalized = (
                f" ({available_fraction:.2%} of active pool)"
                if available_fraction is not None
                else ""
            )
            required_normalized = (
                f" ({required_fraction:.2%} of active pool)"
                if required_fraction is not None
                else ""
            )
            shortfall_normalized = (
                f" ({shortfall_fraction:.2%} of active pool)"
                if shortfall_fraction is not None
                else ""
            )
            reasons.append(
                "resource reserve shortfall "
                f"{assessment.shortfall}{shortfall_normalized} before {assessment.demand.name!r}: "
                f"available {assessment.available_before_start}{available_normalized}, "
                f"required {assessment.requirement.minimum_amount}{required_normalized} "
                f"{assessment.requirement.resource.value}"
            )
        if scorecard.candidate_shortfall:
            reasons.append(f"resource shortfall {scorecard.candidate_shortfall}")
        if scorecard.candidate_specific_unresolved:
            reasons.append(
                f"{len(scorecard.candidate_specific_unresolved)} candidate-specific unresolved evidence item(s)"
            )
        if scorecard.inherited_unresolved:
            reasons.append(
                f"{len(scorecard.inherited_unresolved)} inherited/shared unresolved evidence item(s)"
            )

        objective = scorecard.runtime_uptime_objective_assessment
        if objective is not None:
            target = objective.objective
            scope = f" on {target.bar} bar" if target.bar else ""
            if objective.observed_uptime is None:
                reasons.append(
                    f"runtime uptime objective evidence unavailable for "
                    f"{target.skill_name!r}{scope}"
                )
            else:
                reasons.append(
                    f"runtime uptime objective for {target.skill_name!r}{scope}: "
                    f"observed {objective.observed_uptime:.2%}"
                )

        consequence = scorecard.consequence
        reasons.append(f"resource consequence {consequence.resource_kind.value}")
        reasons.append(
            "resource deltas: "
            f"minimum {consequence.minimum_resource_delta:+d}, "
            f"ending {consequence.ending_resource_delta:+d}, "
            f"cost {consequence.total_cost_delta:+d}, "
            f"waits {consequence.wait_delta:+d}"
        )
        if consequence.minimum_resource_fraction_delta is not None:
            reasons.append(
                "normalized resource deltas: "
                f"minimum {consequence.minimum_resource_fraction_delta:+.2%}, "
                f"ending {(consequence.ending_resource_fraction_delta or 0.0):+.2%}"
            )
        wasted_delta = int(getattr(consequence, "wasted_restore_delta", 0))
        candidate_waste = int(getattr(consequence, "candidate_wasted_restore", 0))
        if wasted_delta or candidate_waste:
            reasons.append(
                "wasted recovery/restoration: "
                f"candidate {candidate_waste}, delta {wasted_delta:+d}"
            )
        total_actions_delta = int(getattr(consequence, "total_actions_delta", 0))
        candidate_total_actions = int(getattr(consequence, "candidate_total_actions", 0))
        if total_actions_delta or candidate_total_actions:
            reasons.append(
                "total action burden: "
                f"candidate {candidate_total_actions}, delta {total_actions_delta:+d}; diagnostic only"
            )
        bar_swap_delta = int(getattr(consequence, "bar_swap_delta", 0))
        candidate_bar_swaps = int(getattr(consequence, "candidate_bar_swaps", 0))
        if bar_swap_delta or candidate_bar_swaps:
            reasons.append(
                "bar-swap burden: "
                f"candidate {candidate_bar_swaps}, delta {bar_swap_delta:+d}"
            )
        heavy_attack_delta = int(getattr(consequence, "heavy_attack_delta", 0))
        candidate_heavy_attacks = int(getattr(consequence, "candidate_heavy_attacks", 0))
        if heavy_attack_delta or candidate_heavy_attacks:
            reasons.append(
                "heavy-attack burden: "
                f"candidate {candidate_heavy_attacks}, delta {heavy_attack_delta:+d}; diagnostic only"
            )
        light_attack_delta = int(getattr(consequence, "light_attack_delta", 0))
        candidate_light_attacks = int(getattr(consequence, "candidate_light_attacks", 0))
        if light_attack_delta or candidate_light_attacks:
            reasons.append(
                "light-attack burden: "
                f"candidate {candidate_light_attacks}, delta {light_attack_delta:+d}; diagnostic only"
            )
        potion_delta = int(getattr(consequence, "potion_delta", 0))
        candidate_potions = int(getattr(consequence, "candidate_potions", 0))
        if potion_delta or candidate_potions:
            reasons.append(
                "potion burden: "
                f"candidate {candidate_potions}, delta {potion_delta:+d}; diagnostic only"
            )
        return tuple(reasons)

    @staticmethod
    def _validate_uptime_objective(
        candidates: tuple[RotationCandidateRankingInput, ...],
    ) -> None:
        keys: set[tuple[str, str | None] | None] = set()
        for item in candidates:
            assessment = item.scorecard.runtime_uptime_objective_assessment
            if assessment is None:
                keys.add(None)
                continue
            keys.add(
                (
                    assessment.objective.skill_name.casefold(),
                    assessment.objective.bar,
                )
            )
        if len(keys) > 1:
            raise ValueError(
                "rotation ranking candidates must use the same runtime uptime objective"
            )
