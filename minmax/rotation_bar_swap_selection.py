from __future__ import annotations

from dataclasses import dataclass

from .rotation_ability_priority import AbilityPriorityList, ResolvedAbilityPriority
from .rotation_action_selection import AbilityActionEligibility, RankedAbilityCandidate
from .rotation_demand_window import RotationDemandWindow


@dataclass(frozen=True)
class RotationBarSwapSelectionResult:
    """Auditable decision about whether priority pressure justifies a bar swap."""

    current_bar: str
    destination_bar: str | None
    demand: RotationDemandWindow | None
    current_bar_best: RankedAbilityCandidate | None
    inactive_bar_best: RankedAbilityCandidate | None
    should_swap: bool
    reason: str


def select_priority_bar_swap(
    *,
    priorities: AbilityPriorityList,
    current_bar: str,
    eligibility: tuple[AbilityActionEligibility, ...],
    demand: RotationDemandWindow | None = None,
) -> RotationBarSwapSelectionResult:
    """Decide whether an explicit bar swap is justified by effective priority.

    The selector never manufactures cooldown, resource, mechanic, or swap-cost
    evidence. It compares only caller-proven legal abilities. A swap is proposed
    when the inactive bar has a legal ability with strictly higher urgency than
    every legal ability on the current bar. Equal priority does not force a swap.
    """

    bar = str(current_bar or "").strip().casefold()
    if bar not in {"front", "back"}:
        raise ValueError("current rotation bar must be front or back")
    destination = "back" if bar == "front" else "front"

    resolved = priorities.resolve(demand)
    priority_by_slot = {(item.entry.bar, item.entry.slot): item for item in resolved}

    eligibility_by_slot: dict[tuple[str, int], AbilityActionEligibility] = {}
    for item in eligibility:
        key = (item.bar, item.slot)
        if key in eligibility_by_slot:
            raise ValueError(
                f"duplicate ability action eligibility for {item.bar} slot {item.slot}"
            )
        priority = priority_by_slot.get(key)
        if priority is None:
            raise ValueError(
                "ability action eligibility targets an unlisted priority slot: "
                f"{item.bar} slot {item.slot}"
            )
        if priority.entry.skill_name != item.skill_name:
            raise ValueError(
                "ability action eligibility skill does not match priority entry: "
                f"{item.skill_name!r} != {priority.entry.skill_name!r}"
            )
        eligibility_by_slot[key] = item

    expected = {(item.entry.bar, item.entry.slot) for item in resolved}
    missing = expected - set(eligibility_by_slot)
    if missing:
        rendered = ", ".join(
            f"{slot_bar} slot {slot}"
            for slot_bar, slot in sorted(missing, key=lambda value: (value[0], value[1]))
        )
        raise ValueError(f"ability action eligibility is incomplete: {rendered}")

    ranked = tuple(
        RankedAbilityCandidate(
            priority=item,
            eligibility=eligibility_by_slot[(item.entry.bar, item.entry.slot)],
        )
        for item in resolved
    )

    current_best = next(
        (
            item
            for item in ranked
            if item.priority.entry.bar == bar and item.eligibility.legal
        ),
        None,
    )
    inactive_best = next(
        (
            item
            for item in ranked
            if item.priority.entry.bar == destination and item.eligibility.legal
        ),
        None,
    )

    if inactive_best is None:
        return RotationBarSwapSelectionResult(
            current_bar=bar,
            destination_bar=None,
            demand=demand,
            current_bar_best=current_best,
            inactive_bar_best=None,
            should_swap=False,
            reason="inactive bar has no legal priority ability",
        )

    if current_best is None:
        return RotationBarSwapSelectionResult(
            current_bar=bar,
            destination_bar=destination,
            demand=demand,
            current_bar_best=None,
            inactive_bar_best=inactive_best,
            should_swap=True,
            reason="inactive bar has a legal ability while current bar has none",
        )

    should_swap = (
        inactive_best.priority.effective_priority
        < current_best.priority.effective_priority
    )
    return RotationBarSwapSelectionResult(
        current_bar=bar,
        destination_bar=destination if should_swap else None,
        demand=demand,
        current_bar_best=current_best,
        inactive_bar_best=inactive_best,
        should_swap=should_swap,
        reason=(
            "inactive bar has strictly higher-priority legal ability"
            if should_swap
            else "current bar retains equal or higher legal priority"
        ),
    )
