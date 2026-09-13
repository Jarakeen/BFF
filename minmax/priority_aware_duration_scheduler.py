from __future__ import annotations

from .duration_aware_rotation_scheduler import DurationAwareRotationScheduler
from .rotation_ability_priority import AbilityPriorityList
from .rotation_plan import RotationAction, RotationActionKind, RotationPlan
from .rotation_recast import RotationRecastRule


class PriorityAwareDurationRotationScheduler(DurationAwareRotationScheduler):
    """Duration-aware scheduler variant that ranks legal same-bar choices by priority.

    The base scheduler remains the compatibility path when no AbilityPriorityList
    is supplied. This variant changes only choices that are already legal: among
    same-bar refreshes that are due, among same-bar no-duration fillers that are
    already eligible, and among displaced/current same-bar actions competing for an
    ordinary decision slot. It does not invent timing readiness, bar swaps,
    resources, encounter legality, or refresh lead windows.

    Lower numeric ability-priority values are higher priority. Equal priorities use
    deterministic saved-slot order from AbilityPriorityList.resolve(), with stable
    action ordering only as the final tie-break.
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

    def _select_displaced_candidate(
        self,
        *,
        queue: list[RotationAction],
        incoming: RotationAction,
        bar: str | None,
    ) -> RotationAction:
        candidates = list(queue)
        candidates.append(incoming)
        ranked = sorted(
            enumerate(candidates),
            key=lambda item: (
                self._priority_key(item[1], bar=bar),
                item[0],
            ),
        )
        selected_index, selected = ranked[0]
        remaining = [
            action
            for index, action in enumerate(candidates)
            if index != selected_index
        ]
        remaining.sort(key=lambda action: self._priority_key(action, bar=bar))
        queue[:] = remaining
        return selected

    def _priority_key(
        self,
        action: RotationAction,
        *,
        bar: str | None,
    ) -> tuple[int, int, str]:
        name = str(action.name or "")
        priority, slot = self._priority_by_key.get(
            (name.casefold(), bar),
            (10**9, 10**9),
        )
        return (priority, slot, name.casefold())
