from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import Enum

from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_execution_burden_service import RotationExecutionBurdenService
from services.rotation_sustain_service import RotationSustainProjection


class RotationResourceConsequenceKind(str, Enum):
    IMPROVED = "improved"
    NEUTRAL = "neutral"
    WORSENED = "worsened"
    MIXED = "mixed"


@dataclass(frozen=True)
class RotationCastCountDelta:
    kind: RotationActionKind
    bar: str | None
    name: str
    baseline_count: int
    candidate_count: int

    @property
    def delta(self) -> int:
        return self.candidate_count - self.baseline_count


@dataclass(frozen=True)
class RotationCostDelta:
    source: str
    baseline_amount: int
    candidate_amount: int

    @property
    def delta(self) -> int:
        return self.candidate_amount - self.baseline_amount


@dataclass(frozen=True)
class RotationPlanConsequence:
    resource_kind: RotationResourceConsequenceKind
    cast_deltas: tuple[RotationCastCountDelta, ...]
    cost_deltas: tuple[RotationCostDelta, ...]
    total_cost_delta: int
    minimum_resource_delta: int
    ending_resource_delta: int
    shortfall_delta: int
    wait_delta: int
    baseline_minimum_resource_fraction: float | None = None
    candidate_minimum_resource_fraction: float | None = None
    minimum_resource_fraction_delta: float | None = None
    baseline_ending_resource_fraction: float | None = None
    candidate_ending_resource_fraction: float | None = None
    ending_resource_fraction_delta: float | None = None
    baseline_wasted_restore: int = 0
    candidate_wasted_restore: int = 0
    wasted_restore_delta: int = 0
    baseline_total_actions: int = 0
    candidate_total_actions: int = 0
    total_actions_delta: int = 0
    baseline_bar_swaps: int = 0
    candidate_bar_swaps: int = 0
    bar_swap_delta: int = 0
    baseline_heavy_attacks: int = 0
    candidate_heavy_attacks: int = 0
    heavy_attack_delta: int = 0


class RotationPlanConsequenceService:
    """Compare two already-generated plans without declaring gameplay quality.

    This service reports the whole-plan consequences of a scheduling change. It
    deliberately classifies only the resource outcome. A plan that spends more
    resource may still be the correct healer plan if it satisfies an encounter
    obligation; role/encounter quality remains caller-owned evidence.

    When the sustain timelines carry canonical maximum-resource evidence, the
    consequence also reports normalized minimum/ending resource fractions. It also
    exposes restoration/recovery wasted against the active ceiling plus explicit
    total-action, bar-swap, and heavy-attack execution burden. These are evidence
    only; this role-neutral layer does not invent universal reserve or
    execution-difficulty thresholds or fold them into the resource classification.
    """

    def __init__(
        self,
        execution_burden_service: RotationExecutionBurdenService | None = None,
    ) -> None:
        self.execution_burden_service = (
            execution_burden_service or RotationExecutionBurdenService()
        )

    def compare(
        self,
        *,
        baseline_plan: RotationPlan,
        candidate_plan: RotationPlan,
        baseline_sustain: RotationSustainProjection,
        candidate_sustain: RotationSustainProjection,
    ) -> RotationPlanConsequence:
        self._validate_identity(baseline_plan, candidate_plan)
        if baseline_sustain.resource is not candidate_sustain.resource:
            raise ValueError("rotation consequence sustain projections must use the same resource")

        baseline_timeline = baseline_sustain.run.timeline
        candidate_timeline = candidate_sustain.run.timeline
        baseline_minimum = self._minimum_amount(baseline_timeline)
        candidate_minimum = self._minimum_amount(candidate_timeline)
        ending_delta = candidate_timeline.ending_amount - baseline_timeline.ending_amount
        minimum_delta = candidate_minimum - baseline_minimum
        shortfall_delta = candidate_timeline.total_shortfall - baseline_timeline.total_shortfall
        wait_delta = self._wait_count(candidate_plan) - self._wait_count(baseline_plan)

        baseline_minimum_fraction = self._minimum_fraction(baseline_timeline)
        candidate_minimum_fraction = self._minimum_fraction(candidate_timeline)
        baseline_ending_fraction = self._ending_fraction(baseline_timeline)
        candidate_ending_fraction = self._ending_fraction(candidate_timeline)
        baseline_wasted_restore = self._wasted_restore(baseline_timeline)
        candidate_wasted_restore = self._wasted_restore(candidate_timeline)
        execution_burden = self.execution_burden_service.compare(
            baseline_plan=baseline_plan,
            candidate_plan=candidate_plan,
        )

        cast_deltas = self._cast_deltas(baseline_plan, candidate_plan)
        cost_deltas = self._cost_deltas(baseline_sustain, candidate_sustain)
        total_cost_delta = sum(item.delta for item in cost_deltas)

        return RotationPlanConsequence(
            resource_kind=self._resource_kind(
                minimum_delta=minimum_delta,
                ending_delta=ending_delta,
                shortfall_delta=shortfall_delta,
            ),
            cast_deltas=cast_deltas,
            cost_deltas=cost_deltas,
            total_cost_delta=total_cost_delta,
            minimum_resource_delta=minimum_delta,
            ending_resource_delta=ending_delta,
            shortfall_delta=shortfall_delta,
            wait_delta=wait_delta,
            baseline_minimum_resource_fraction=baseline_minimum_fraction,
            candidate_minimum_resource_fraction=candidate_minimum_fraction,
            minimum_resource_fraction_delta=self._optional_delta(
                baseline_minimum_fraction,
                candidate_minimum_fraction,
            ),
            baseline_ending_resource_fraction=baseline_ending_fraction,
            candidate_ending_resource_fraction=candidate_ending_fraction,
            ending_resource_fraction_delta=self._optional_delta(
                baseline_ending_fraction,
                candidate_ending_fraction,
            ),
            baseline_wasted_restore=baseline_wasted_restore,
            candidate_wasted_restore=candidate_wasted_restore,
            wasted_restore_delta=candidate_wasted_restore - baseline_wasted_restore,
            baseline_total_actions=execution_burden.baseline.total_actions,
            candidate_total_actions=execution_burden.candidate.total_actions,
            total_actions_delta=execution_burden.total_actions_delta,
            baseline_bar_swaps=execution_burden.baseline.bar_swaps,
            candidate_bar_swaps=execution_burden.candidate.bar_swaps,
            bar_swap_delta=execution_burden.bar_swaps_delta,
            baseline_heavy_attacks=execution_burden.baseline.heavy_attacks,
            candidate_heavy_attacks=execution_burden.candidate.heavy_attacks,
            heavy_attack_delta=execution_burden.heavy_attacks_delta,
        )

    @staticmethod
    def _validate_identity(baseline: RotationPlan, candidate: RotationPlan) -> None:
        if baseline.character_name.casefold() != candidate.character_name.casefold():
            raise ValueError("rotation consequence plans must belong to the same character")
        if baseline.build_name.casefold() != candidate.build_name.casefold():
            raise ValueError("rotation consequence plans must belong to the same build")
        if baseline.duration_seconds != candidate.duration_seconds:
            raise ValueError("rotation consequence plans must use the same duration")

    @staticmethod
    def _minimum_amount(timeline: ResourceTimelineResult) -> int:
        values = [timeline.starting_amount]
        values.extend(event.after for event in timeline.events)
        return min(values) if values else timeline.starting_amount

    @staticmethod
    def _minimum_fraction(timeline: ResourceTimelineResult) -> float | None:
        current_maximum = getattr(timeline, "starting_maximum", None)
        if current_maximum is None or int(current_maximum) <= 0:
            return None

        fractions = [float(timeline.starting_amount) / float(current_maximum)]
        for event in timeline.events:
            maximum_after = getattr(event, "maximum_after", None)
            if maximum_after is not None:
                current_maximum = int(maximum_after)
            if int(current_maximum) <= 0:
                return None
            fractions.append(float(event.after) / float(current_maximum))
        return min(fractions)

    @staticmethod
    def _ending_fraction(timeline: ResourceTimelineResult) -> float | None:
        ending_maximum = getattr(timeline, "ending_maximum", None)
        if ending_maximum is None or int(ending_maximum) <= 0:
            return None
        return float(timeline.ending_amount) / float(ending_maximum)

    @staticmethod
    def _wasted_restore(timeline: ResourceTimelineResult) -> int:
        return sum(int(getattr(event, "wasted_restore", 0) or 0) for event in timeline.events)

    @staticmethod
    def _optional_delta(baseline: float | None, candidate: float | None) -> float | None:
        if baseline is None or candidate is None:
            return None
        return candidate - baseline

    @staticmethod
    def _wait_count(plan: RotationPlan) -> int:
        return sum(action.kind is RotationActionKind.WAIT for action in plan.actions)

    @staticmethod
    def _cast_key(action) -> tuple[RotationActionKind, str | None, str]:
        return (action.kind, action.bar, str(action.name or ""))

    @classmethod
    def _cast_deltas(
        cls,
        baseline: RotationPlan,
        candidate: RotationPlan,
    ) -> tuple[RotationCastCountDelta, ...]:
        included = {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
        before = Counter(
            cls._cast_key(action)
            for action in baseline.actions
            if action.kind in included and action.name
        )
        after = Counter(
            cls._cast_key(action)
            for action in candidate.actions
            if action.kind in included and action.name
        )
        keys = sorted(
            set(before) | set(after),
            key=lambda key: (key[1] or "", key[2].casefold(), key[0].value),
        )
        return tuple(
            RotationCastCountDelta(
                kind=key[0],
                bar=key[1],
                name=key[2],
                baseline_count=before[key],
                candidate_count=after[key],
            )
            for key in keys
            if before[key] != after[key]
        )

    @staticmethod
    def _cost_totals(projection: RotationSustainProjection) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for event in projection.run.action_cost_events:
            totals[str(event.source)] += int(event.amount)
        return dict(totals)

    @classmethod
    def _cost_deltas(
        cls,
        baseline: RotationSustainProjection,
        candidate: RotationSustainProjection,
    ) -> tuple[RotationCostDelta, ...]:
        before = cls._cost_totals(baseline)
        after = cls._cost_totals(candidate)
        keys = sorted(set(before) | set(after), key=str.casefold)
        return tuple(
            RotationCostDelta(
                source=key,
                baseline_amount=before.get(key, 0),
                candidate_amount=after.get(key, 0),
            )
            for key in keys
            if before.get(key, 0) != after.get(key, 0)
        )

    @staticmethod
    def _resource_kind(
        *,
        minimum_delta: int,
        ending_delta: int,
        shortfall_delta: int,
    ) -> RotationResourceConsequenceKind:
        if shortfall_delta > 0:
            return RotationResourceConsequenceKind.WORSENED
        if shortfall_delta < 0:
            if minimum_delta >= 0 and ending_delta >= 0:
                return RotationResourceConsequenceKind.IMPROVED
            return RotationResourceConsequenceKind.MIXED

        deltas = (minimum_delta, ending_delta)
        if deltas == (0, 0):
            return RotationResourceConsequenceKind.NEUTRAL
        if all(value >= 0 for value in deltas) and any(value > 0 for value in deltas):
            return RotationResourceConsequenceKind.IMPROVED
        if all(value <= 0 for value in deltas) and any(value < 0 for value in deltas):
            return RotationResourceConsequenceKind.WORSENED
        return RotationResourceConsequenceKind.MIXED
