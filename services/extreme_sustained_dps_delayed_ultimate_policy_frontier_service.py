from __future__ import annotations

"""Finite delayed-Ultimate timing frontier over one exact RotationPlan.

The frontier enumerates every legal sequence of Ultimate casts that can replace
scheduled same-bar SKILL slots while respecting one explicit Ultimate resource
timeline. Generation at the exact cast timestamp is never borrowed ahead of the
cast, matching RotationScheduledActionResourceLegalityService semantics.
"""

from dataclasses import dataclass

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_ultimate import UltimateRotationScheduler, UltimateScheduleRule
from minmax.ultimate_resource_timeline import UltimateGenerationEvent, UltimateSpendRule


_EPSILON = 1e-9


@dataclass(frozen=True)
class ExtremeSustainedDPSDelayedUltimatePolicy:
    policy_id: str
    cast_slots: tuple[tuple[float, int], ...]
    plan: RotationPlan
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeSustainedDPSDelayedUltimatePolicyFrontier:
    policies: tuple[ExtremeSustainedDPSDelayedUltimatePolicy, ...]
    candidate_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSDelayedUltimatePolicyFrontierService:
    """Enumerate all legal delayed casts on scheduled same-bar skill slots."""

    def __init__(self, *, scheduler: UltimateRotationScheduler | None = None) -> None:
        self.scheduler = scheduler or UltimateRotationScheduler()

    @staticmethod
    def _eligible_slots(
        plan: RotationPlan,
        *,
        bar: str,
    ) -> tuple[RotationAction, ...]:
        target_bar = str(bar or "").strip().casefold()
        if target_bar not in {"front", "back"}:
            raise ValueError("delayed Ultimate frontier requires front or back bar")
        return tuple(
            action
            for action in plan.actions
            if action.kind is RotationActionKind.SKILL
            and action.bar == target_bar
        )

    @staticmethod
    def _generation_before(
        events: tuple[UltimateGenerationEvent, ...],
        *,
        time_seconds: float,
    ) -> float:
        return sum(
            float(event.amount)
            for event in events
            if float(event.time_seconds) < float(time_seconds) - _EPSILON
        )

    @classmethod
    def _legal_slot_sequences(
        cls,
        *,
        slots: tuple[RotationAction, ...],
        starting_ultimate: float,
        generation_events: tuple[UltimateGenerationEvent, ...],
        cost: float,
    ) -> tuple[tuple[tuple[float, int], ...], ...]:
        ordered_events = tuple(
            sorted(
                generation_events,
                key=lambda row: (row.time_seconds, row.source.casefold()),
            )
        )
        prefix_generation = tuple(
            cls._generation_before(
                ordered_events,
                time_seconds=slot.time_seconds,
            )
            for slot in slots
        )

        result: list[tuple[tuple[float, int], ...]] = []

        def visit(
            index: int,
            spent: float,
            selected: tuple[tuple[float, int], ...],
        ) -> None:
            if index >= len(slots):
                result.append(selected)
                return

            slot = slots[index]
            visit(index + 1, spent, selected)

            available = (
                float(starting_ultimate)
                + float(prefix_generation[index])
                - float(spent)
            )
            if available + _EPSILON >= float(cost):
                visit(
                    index + 1,
                    spent + float(cost),
                    selected + ((float(slot.time_seconds), int(slot.sequence)),),
                )

        visit(0, 0.0, ())
        return tuple(
            sorted(
                result,
                key=lambda rows: (
                    len(rows),
                    rows,
                ),
            )
        )

    def build(
        self,
        *,
        plan: RotationPlan,
        bar: str,
        spend_rule: UltimateSpendRule,
        starting_ultimate: float,
        generation_events: tuple[UltimateGenerationEvent, ...] = (),
    ) -> ExtremeSustainedDPSDelayedUltimatePolicyFrontier:
        target_bar = str(bar or "").strip().casefold()
        slots = self._eligible_slots(plan, bar=target_bar)
        unresolved: list[str] = []

        events = tuple(
            sorted(
                tuple(generation_events),
                key=lambda row: (row.time_seconds, row.source.casefold()),
            )
        )
        if any(event.time_seconds > plan.duration_seconds for event in events):
            raise ValueError(
                "Ultimate generation event cannot occur after rotation duration"
            )

        sequences = self._legal_slot_sequences(
            slots=slots,
            starting_ultimate=float(starting_ultimate),
            generation_events=events,
            cost=float(spend_rule.cost),
        )

        policies: list[ExtremeSustainedDPSDelayedUltimatePolicy] = []
        for index, sequence in enumerate(sequences):
            if not sequence:
                scheduled = plan
                policy_id = "ultimate:none"
            else:
                rule = UltimateScheduleRule(
                    skill_name=spend_rule.skill_name,
                    bar=target_bar,
                    cost=float(spend_rule.cost),
                    available_at_seconds=tuple(
                        time_seconds
                        for time_seconds, _sequence in sequence
                    ),
                )
                scheduled = self.scheduler.apply(plan, (rule,))
                actual = tuple(
                    (float(action.time_seconds), int(action.sequence))
                    for action in scheduled.actions
                    if action.kind is RotationActionKind.ULTIMATE
                    and action.name == spend_rule.skill_name
                    and action.bar == target_bar
                )
                if actual != sequence:
                    unresolved.append(
                        "Delayed Ultimate scheduler did not preserve selected cast-slot identity "
                        f"for candidate {index}: selected={sequence!r}, scheduled={actual!r}"
                    )
                policy_id = "ultimate:" + ",".join(
                    f"{time:g}/{seq}"
                    for time, seq in sequence
                )

            policies.append(
                ExtremeSustainedDPSDelayedUltimatePolicy(
                    policy_id=policy_id,
                    cast_slots=sequence,
                    plan=scheduled,
                    evidence=(
                        f"Selected delayed Ultimate casts: {len(sequence)}",
                        "Ultimate casts replace only scheduled same-bar SKILL slots",
                        "Resource affordability uses only generation strictly before each cast timestamp",
                    ),
                    unresolved=(),
                )
            )

        deduped = tuple(dict.fromkeys(unresolved))
        return ExtremeSustainedDPSDelayedUltimatePolicyFrontier(
            policies=tuple(policies),
            candidate_count=len(policies),
            denominator_proven=bool(policies and not deduped),
            evidence=(
                f"Eligible {target_bar}-bar skill slots: {len(slots)}",
                f"Legal delayed Ultimate policies: {len(policies)}",
                f"Ultimate cost: {float(spend_rule.cost):g}",
                f"Starting Ultimate: {float(starting_ultimate):g}",
                "Every legal cast/skip branch over the exact seed-plan same-bar skill slots is enumerated",
                "Same-timestamp Ultimate generation is deliberately unavailable to the cast at that timestamp",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSDelayedUltimatePolicy",
    "ExtremeSustainedDPSDelayedUltimatePolicyFrontier",
    "ExtremeSustainedDPSDelayedUltimatePolicyFrontierService",
]
