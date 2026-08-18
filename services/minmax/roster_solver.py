from dataclasses import dataclass

from .group_evaluation import GroupEvaluation
from .group_evaluator import GroupEvaluator
from .roster import RosterCandidate, RosterRequest
from .role import Role



@dataclass(frozen=True)
class RosterOptimizationResult:
    roster: list[RosterCandidate]
    evaluation: GroupEvaluation
    score: float
    explanations: list[str]


class RosterSolver:

    def __init__(
        self,
        evaluator: GroupEvaluator | None = None,
    ):
        self.evaluator = evaluator or GroupEvaluator()

    def solve(
        self,
        request: RosterRequest,
        candidates: list[RosterCandidate],
    ) -> RosterOptimizationResult:

        selected = self._select_candidates(
            request=request,
            candidates=candidates,
        )

        evaluation = self.evaluator.evaluate(selected)

        explanations = self._build_explanations(
            request=request,
            roster=selected,
            evaluation=evaluation,
        )

        return RosterOptimizationResult(
            roster=selected,
            evaluation=evaluation,
            score=evaluation.group_damage,
            explanations=explanations,
        )

    def _select_candidates(
        self,
        *,
        request: RosterRequest,
        candidates: list[RosterCandidate],
    ) -> list[RosterCandidate]:

        selected: list[RosterCandidate] = []

        role_requirements = getattr(
            request,
            "role_requirements",
            [],
        )

        candidate_requirements = getattr(
            request,
            "candidate_requirements",
            [],
        )

        fixed_role_counts = {
            role: sum(
                1
                for slot in request.fixed_slots
                if slot.role == role
            )
            for role in Role
        }

        # Fulfill explicit role requirements after accounting
        # for roles already occupied by fixed slots.
        for requirement in role_requirements:

            already_fixed = fixed_role_counts.get(
                requirement.role,
                0,
            )

            already_selected = sum(
                1
                for candidate in selected
                if candidate.role == requirement.role
            )

            needed = (
                requirement.count
                - already_fixed
                - already_selected
            )

            if needed <= 0:
                continue

            available = [
                candidate
                for candidate in candidates
                if candidate.role == requirement.role
                and candidate not in selected
            ]

            available.sort(
                key=lambda candidate: candidate.personal_damage,
                reverse=True,
            )

            if len(available) < needed:
                raise ValueError(
                    f"Not enough candidates for required role "
                    f"{requirement.role.value}: "
                    f"needed {needed}, "
                    f"found {len(available)}"
                )

            selected.extend(available[:needed])

        # Fulfill specific candidate requirements.
        #
        # These are more restrictive than a simple role requirement.
        # Example:
        #   Tank + Necromancer
        #   Healer + Arcanist
        #   DD + minimum 165K DPS
        for requirement in candidate_requirements:

            matching_candidates = [
                candidate
                for candidate in candidates
                if candidate not in selected
                and requirement.matches(candidate)
            ]

            if not matching_candidates:
                raise ValueError(
                    f"No candidate satisfies requirement: "
                    f"{requirement}"
                )

            # For candidates that satisfy the requirement,
            # prefer the strongest candidate for a
            # max-group-damage objective.
            matching_candidates.sort(
                key=lambda candidate: (
                    candidate.personal_damage,
                    candidate.support_value,
                ),
                reverse=True,
            )

            needed = requirement.count

            if len(matching_candidates) < needed:
                raise ValueError(
                    f"Not enough candidates for requirement "
                    f"{requirement}: "
                    f"needed {needed}, "
                    f"found {len(matching_candidates)}"
                )

            selected.extend(
                matching_candidates[:needed]
            )

        # Fill whatever slots remain after satisfying
        # explicit role requirements and candidate requirements.
        remaining = request.remaining_slots - len(selected)

        if remaining > 0:

            available = [
                candidate
                for candidate in candidates
                if candidate not in selected
            ]

            available.sort(
                key=lambda candidate: (
                    candidate.personal_damage,
                    candidate.support_value,
                ),
                reverse=True,
            )

            selected.extend(
                available[:remaining]
            )

        if len(selected) < request.remaining_slots:
            raise ValueError(
                f"Unable to build a full roster: "
                f"needed {request.remaining_slots} "
                f"available slots, "
                f"found {len(selected)} candidates"
            )

        return selected

    def _evaluate_group(
        self,
        roster: list[RosterCandidate],
    ) -> GroupEvaluation:

        return GroupEvaluation(
            group_damage=sum(
                candidate.personal_damage
                for candidate in roster
            ),
            support_score=sum(
                candidate.support_value
                for candidate in roster
            ),
            survivability_score=sum(
                candidate.survivability
                for candidate in roster
            ),
            mechanic_score=sum(
                candidate.mechanic_value
                for candidate in roster
            ),
        )

    def _build_explanations(
        self,
        *,
        request: RosterRequest,
        roster: list[RosterCandidate],
        evaluation: GroupEvaluation,
    ) -> list[str]:

        explanations = [
            f"Selected {len(roster)} candidates for "
            f"{request.remaining_slots} open slots."
        ]

        explanations.append(
            f"Group damage score: {evaluation.group_damage:.1f}"
        )

        return explanations

