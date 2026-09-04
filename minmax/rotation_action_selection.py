from __future__ import annotations

from dataclasses import dataclass

from .rotation_ability_priority import AbilityPriorityList, ResolvedAbilityPriority
from .rotation_demand_window import RotationDemandWindow


@dataclass(frozen=True)
class AbilityActionEligibility:
    """Caller-proven legality for one exact saved-bar ability at a decision point.

    This layer deliberately does not calculate costs, cooldowns, effect expiry,
    range, mechanics, or reserve safety. Those facts remain owned by the existing
    engines and are supplied here as explicit evidence.
    """

    bar: str
    slot: int
    skill_name: str
    timing_ready: bool = True
    resource_safe: bool = True
    encounter_allowed: bool = True
    reason: str | None = None

    def __post_init__(self) -> None:
        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("ability action eligibility bar must be front or back")
        object.__setattr__(self, "bar", bar)

        slot = int(self.slot)
        if slot < 1 or slot > 6:
            raise ValueError("ability action eligibility slot must be between 1 and 6")
        object.__setattr__(self, "slot", slot)

        skill_name = str(self.skill_name or "").strip()
        if not skill_name:
            raise ValueError("ability action eligibility skill name is required")
        object.__setattr__(self, "skill_name", skill_name)

        if self.reason is not None:
            reason = str(self.reason).strip()
            object.__setattr__(self, "reason", reason or None)

    @property
    def legal(self) -> bool:
        return self.timing_ready and self.resource_safe and self.encounter_allowed


@dataclass(frozen=True)
class RankedAbilityCandidate:
    priority: ResolvedAbilityPriority
    eligibility: AbilityActionEligibility


@dataclass(frozen=True)
class RotationActionSelectionResult:
    """Auditable priority-driven action choice for one decision point."""

    current_bar: str
    demand: RotationDemandWindow | None
    ranked_candidates: tuple[RankedAbilityCandidate, ...]
    selected: RankedAbilityCandidate | None
    rejected: tuple[RankedAbilityCandidate, ...]


def select_priority_ability_action(
    *,
    priorities: AbilityPriorityList,
    current_bar: str,
    eligibility: tuple[AbilityActionEligibility, ...],
    demand: RotationDemandWindow | None = None,
) -> RotationActionSelectionResult:
    """Select the highest-priority legal ability on the currently active bar.

    Effective priority comes only from ``AbilityPriorityList``. Legality comes
    only from caller-supplied evidence. Abilities on the inactive bar are not
    silently selected; bar-swap policy is a separate scheduling decision.
    Equal-priority abilities retain canonical priority-list presentation order,
    which is deterministic but does not manufacture a hidden combat preference.
    """

    bar = str(current_bar or "").strip().casefold()
    if bar not in {"front", "back"}:
        raise ValueError("current rotation bar must be front or back")

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

    expected_slots = {(item.entry.bar, item.entry.slot) for item in resolved}
    missing = expected_slots - set(eligibility_by_slot)
    if missing:
        rendered = ", ".join(
            f"{slot_bar} slot {slot}"
            for slot_bar, slot in sorted(missing, key=lambda value: (value[0], value[1]))
        )
        raise ValueError(f"ability action eligibility is incomplete: {rendered}")

    candidates = tuple(
        RankedAbilityCandidate(
            priority=item,
            eligibility=eligibility_by_slot[(item.entry.bar, item.entry.slot)],
        )
        for item in resolved
        if item.entry.bar == bar
    )

    selected = next((item for item in candidates if item.eligibility.legal), None)
    rejected = tuple(
        item
        for item in candidates
        if selected is None
        or item is not selected
        and (
            not item.eligibility.legal
            or item.priority.effective_priority <= selected.priority.effective_priority
        )
    )

    return RotationActionSelectionResult(
        current_bar=bar,
        demand=demand,
        ranked_candidates=candidates,
        selected=selected,
        rejected=rejected,
    )
