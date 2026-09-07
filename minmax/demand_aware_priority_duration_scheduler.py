from __future__ import annotations

from .priority_aware_duration_scheduler import PriorityAwareDurationRotationScheduler
from .rotation_ability_priority import AbilityPriorityList
from .rotation_demand_window import RotationDemandWindow
from .rotation_plan import RotationActionKind


class DemandAwarePriorityDurationRotationScheduler(
    PriorityAwareDurationRotationScheduler
):
    """Resolve due-refresh priority against the encounter demand active now.

    Base priorities remain the compatibility path outside a demand window. When one
    explicit demand window is active at the decision timestamp, matching
    AbilityPriorityOverride entries become effective through AbilityPriorityList.

    Overlapping demand windows are rejected here rather than silently inventing an
    encounter priority between simultaneous mechanics. The caller must resolve that
    ambiguity before scheduling.
    """

    def __init__(
        self,
        priorities: AbilityPriorityList,
        demands: tuple[RotationDemandWindow, ...],
    ) -> None:
        super().__init__(priorities)
        self.demands = tuple(demands)

    def _active_demand(self, time_seconds: float) -> RotationDemandWindow | None:
        active = tuple(
            demand
            for demand in self.demands
            if demand.start_seconds <= float(time_seconds) < demand.end_seconds
        )
        if len(active) > 1:
            rendered = ", ".join(demand.name for demand in active)
            raise ValueError(
                "multiple rotation demand windows are active at "
                f"{float(time_seconds):g}s: {rendered}; caller must resolve demand precedence"
            )
        return active[0] if active else None

    def _due_refresh(
        self,
        *,
        time_seconds: float,
        bar: str | None,
        next_due: dict[tuple[str, str | None], float],
        rule_order: dict[tuple[str, str | None], int],
        action_kind_by_key: dict[tuple[str, str | None], RotationActionKind],
    ) -> tuple[str, str | None] | None:
        demand = self._active_demand(time_seconds)
        priority_by_key = {
            (item.entry.skill_name.casefold(), item.entry.bar): (
                item.effective_priority,
                item.entry.slot,
            )
            for item in self.priorities.resolve(demand)
        }

        candidates = []
        for key, due in next_due.items():
            if (
                key[1] != bar
                or due > time_seconds
                or action_kind_by_key.get(key) is not RotationActionKind.SKILL
            ):
                continue
            priority, slot = priority_by_key.get(
                key,
                (10**9, rule_order.get(key, 10**9)),
            )
            candidates.append(
                (
                    priority,
                    due,
                    slot,
                    rule_order.get(key, 10**9),
                    key,
                )
            )

        if not candidates:
            return None
        candidates.sort(
            key=lambda item: (item[0], item[1], item[2], item[3], item[4][0])
        )
        return candidates[0][4]
