from __future__ import annotations

from .duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from .rotation_ability_priority import AbilityPriorityList
from .rotation_plan import RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule


class PriorityAwareDurationRotationScheduler(DurationAwareRotationScheduler):
    """Duration-aware scheduler variant that ranks due refreshes and fillers by priority.

    The base scheduler remains the compatibility path when no AbilityPriorityList
    is supplied. This variant changes only choices that are already legal: among
    same-bar refreshes that are due, and among same-bar no-duration fillers that are
    already eligible. It does not invent timing readiness, bar swaps, resources,
    encounter legality, or refresh lead windows.

    Lower numeric ability-priority values are higher priority. For equal priority,
    due refreshes prefer the earlier due time, while fillers use deterministic saved
    slot order from AbilityPriorityList.resolve().
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

    def _fillers(
        self,
        plan: RotationPlan,
        rule_map: dict[tuple[str, str | None], RotationRecastRule],
    ) -> dict[str, tuple[str, ...]]:
        fillers = super()._fillers(plan, rule_map)
        ranked: dict[str, tuple[str, ...]] = {}
        for bar, values in fillers.items():
            ranked[bar] = tuple(
                sorted(
                    values,
                    key=lambda skill_name: (
                        self._priority_by_key.get(
                            (skill_name.casefold(), bar),
                            (10**9, 10**9),
                        )[0],
                        self._priority_by_key.get(
                            (skill_name.casefold(), bar),
                            (10**9, 10**9),
                        )[1],
                        skill_name.casefold(),
                    ),
                )
            )
        return ranked
