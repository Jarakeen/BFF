from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationExecutionBurden:
    total_actions: int
    skill_casts: int
    ultimate_casts: int
    light_attacks: int
    heavy_attacks: int
    potions: int
    bar_swaps: int
    waits: int


@dataclass(frozen=True)
class RotationExecutionBurdenDelta:
    baseline: RotationExecutionBurden
    candidate: RotationExecutionBurden

    @property
    def total_actions_delta(self) -> int:
        return self.candidate.total_actions - self.baseline.total_actions

    @property
    def skill_casts_delta(self) -> int:
        return self.candidate.skill_casts - self.baseline.skill_casts

    @property
    def ultimate_casts_delta(self) -> int:
        return self.candidate.ultimate_casts - self.baseline.ultimate_casts

    @property
    def light_attacks_delta(self) -> int:
        return self.candidate.light_attacks - self.baseline.light_attacks

    @property
    def heavy_attacks_delta(self) -> int:
        return self.candidate.heavy_attacks - self.baseline.heavy_attacks

    @property
    def potions_delta(self) -> int:
        return self.candidate.potions - self.baseline.potions

    @property
    def bar_swaps_delta(self) -> int:
        return self.candidate.bar_swaps - self.baseline.bar_swaps

    @property
    def waits_delta(self) -> int:
        return self.candidate.waits - self.baseline.waits


class RotationExecutionBurdenService:
    """Report explicit schedule complexity without inventing a weighted burden score.

    Counts are role-neutral evidence only. This layer deliberately does not claim
    that one extra bar swap is equivalent to one extra heavy attack, skill cast,
    potion, or wait. Ranking/policy layers may consume individual dimensions when
    they have an explicit reason to do so.
    """

    @staticmethod
    def assess(plan: RotationPlan) -> RotationExecutionBurden:
        counts = {kind: 0 for kind in RotationActionKind}
        for action in plan.actions:
            counts[action.kind] += 1

        return RotationExecutionBurden(
            total_actions=len(plan.actions),
            skill_casts=counts[RotationActionKind.SKILL],
            ultimate_casts=counts[RotationActionKind.ULTIMATE],
            light_attacks=counts[RotationActionKind.LIGHT_ATTACK],
            heavy_attacks=counts[RotationActionKind.HEAVY_ATTACK],
            potions=counts[RotationActionKind.POTION],
            bar_swaps=counts[RotationActionKind.BAR_SWAP],
            waits=counts[RotationActionKind.WAIT],
        )

    def compare(
        self,
        *,
        baseline_plan: RotationPlan,
        candidate_plan: RotationPlan,
    ) -> RotationExecutionBurdenDelta:
        self._validate_identity(baseline_plan, candidate_plan)
        return RotationExecutionBurdenDelta(
            baseline=self.assess(baseline_plan),
            candidate=self.assess(candidate_plan),
        )

    @staticmethod
    def _validate_identity(baseline: RotationPlan, candidate: RotationPlan) -> None:
        if baseline.character_name.casefold() != candidate.character_name.casefold():
            raise ValueError("rotation burden plans must belong to the same character")
        if baseline.build_name.casefold() != candidate.build_name.casefold():
            raise ValueError("rotation burden plans must belong to the same build")
        if baseline.duration_seconds != candidate.duration_seconds:
            raise ValueError("rotation burden plans must use the same duration")
