from __future__ import annotations

from .duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from .rotation_ability_priority import AbilityPriorityList
from .rotation_plan import RotationActionKind


class PriorityAwareDurationRotationScheduler(DurationAwareRotationScheduler):
    """Duration-aware scheduler variant that ranks due refreshes by explicit priority.

    The base scheduler remains the compatibility path when no AbilityPriorityList
    is supplied. This variant changes only the choice among same-bar refreshes that
    are already due. It does not invent timing readiness, bar swaps, resources,
    encounter legality, or refresh lead windows.

    Lower numeric ability-priority values are higher priority. For equal priority,
    the earlier due time wins, followed by deterministic saved-slot presentation
    order from AbilityPriorityList.resolve().
    """

    def __init__(self, priorities: AbilityPriorityList) -> None:
        self.priorities = priorities
        self._priority_by_key = {
            (item.entry.skill_name.casefold(), item.entry.bar): (
                item.effective_priority,
                item.entry.slot,
            )
            for item in priorities.resolve()
        }

    def _due_refresh(
        self,
        *,
        time_seconds: float,
        bar: str | None,
        next_due: dict[tuple[str, str | None], float],
        rule_order: dict[tuple[str, str | None], int],
        action_kind_by_key: dict[tuple[str, str | None], RotationActionKind],
    ) -> tuple[str, str | None] | None:
        candidates = []
        for key, due in next_due.items():
            if (
                key[1] != bar
                or due > time_seconds
                or action_kind_by_key.get(key) is not RotationActionKind.SKILL
            ):
                continue
            priority, slot = self._priority_by_key.get(
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
        candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4][0]))
        return candidates[0][4]
