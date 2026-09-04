from __future__ import annotations

from dataclasses import dataclass

from .healer_rotation_policy import HealerRotationPolicySet, HealerRotationTag
from .rotation_ability_priority import (
    AbilityPriorityEntry,
    AbilityPriorityList,
    AbilityPriorityOverride,
)


@dataclass(frozen=True)
class HealerTagPriority:
    """Explicit numeric priority assigned to one healer policy tag.

    Lower values are higher urgency. The caller owns these values; this module
    does not invent universal healer rankings from skill names or tag labels.
    """

    tag: HealerRotationTag
    priority: int

    def __post_init__(self) -> None:
        tag = self.tag if isinstance(self.tag, HealerRotationTag) else HealerRotationTag(str(self.tag))
        priority = int(self.priority)
        if priority < 0:
            raise ValueError("healer tag priority cannot be negative")
        object.__setattr__(self, "tag", tag)
        object.__setattr__(self, "priority", priority)


@dataclass(frozen=True)
class HealerDemandTagPriorities:
    """Explicit demand-specific priority policy for healer rotation tags."""

    demand_name: str
    priorities: tuple[HealerTagPriority, ...]
    reason: str | None = None

    def __post_init__(self) -> None:
        name = str(self.demand_name or "").strip()
        if not name:
            raise ValueError("healer demand priority requires a demand name")
        object.__setattr__(self, "demand_name", name)
        _priority_map(self.priorities, label=f"demand {name}")
        if self.reason is not None:
            reason = str(self.reason).strip()
            object.__setattr__(self, "reason", reason or None)


def _priority_map(
    priorities: tuple[HealerTagPriority, ...],
    *,
    label: str,
) -> dict[HealerRotationTag, int]:
    by_tag: dict[HealerRotationTag, int] = {}
    for item in priorities:
        if item.tag in by_tag:
            raise ValueError(f"duplicate healer tag priority in {label}: {item.tag.value}")
        by_tag[item.tag] = item.priority
    if not by_tag:
        raise ValueError(f"healer tag priority policy cannot be empty: {label}")
    return by_tag


def _resolve_skill_priority(
    tags: tuple[HealerRotationTag, ...],
    priority_by_tag: dict[HealerRotationTag, int],
    *,
    skill_name: str,
    context: str,
) -> int:
    matches = tuple(priority_by_tag[tag] for tag in tags if tag in priority_by_tag)
    if not matches:
        rendered = ", ".join(tag.value for tag in tags)
        raise ValueError(
            f"healer ability priority has no matching tag priority for {skill_name} "
            f"in {context}: {rendered}"
        )
    return min(matches)


def generate_healer_ability_priority_list(
    *,
    policy_set: HealerRotationPolicySet,
    base_priorities: tuple[HealerTagPriority, ...],
    demand_priorities: tuple[HealerDemandTagPriorities, ...] = (),
) -> AbilityPriorityList:
    """Generate role-neutral ability priority entries from explicit healer tags.

    Every classified healer skill must match at least one supplied base tag
    priority. A multi-tag ability inherits the numerically smallest matching
    value, representing the highest urgency explicitly granted by the caller.

    Demand policies work the same way but create overrides only when at least one
    of the skill's tags is mentioned by that demand. Skills untouched by a demand
    keep their base priority. No priority is inferred from skill names, bar order,
    slot order, or ESO role stereotypes.
    """

    if policy_set.unresolved:
        raise ValueError("healer ability priority generation requires fully classified policy")

    base_by_tag = _priority_map(base_priorities, label="base")
    demand_by_name: dict[str, HealerDemandTagPriorities] = {}
    for demand in demand_priorities:
        if demand.demand_name in demand_by_name:
            raise ValueError(
                f"duplicate healer demand priority policy: {demand.demand_name}"
            )
        demand_by_name[demand.demand_name] = demand

    entries: list[AbilityPriorityEntry] = []
    for item in policy_set.policies:
        policy = item.policy
        entries.append(
            AbilityPriorityEntry(
                bar=policy.bar,
                slot=policy.slot,
                skill_name=policy.skill_name,
                priority=_resolve_skill_priority(
                    policy.tags,
                    base_by_tag,
                    skill_name=policy.skill_name,
                    context="base policy",
                ),
            )
        )

    overrides: list[AbilityPriorityOverride] = []
    for demand_name, demand in demand_by_name.items():
        demand_map = _priority_map(
            demand.priorities,
            label=f"demand {demand_name}",
        )
        for item in policy_set.policies:
            policy = item.policy
            matching = tuple(demand_map[tag] for tag in policy.tags if tag in demand_map)
            if not matching:
                continue
            overrides.append(
                AbilityPriorityOverride(
                    demand_name=demand_name,
                    bar=policy.bar,
                    slot=policy.slot,
                    skill_name=policy.skill_name,
                    priority=min(matching),
                    reason=demand.reason,
                )
            )

    return AbilityPriorityList(
        character_name=policy_set.character_name,
        build_name=policy_set.build_name,
        role="Healer",
        entries=tuple(entries),
        overrides=tuple(overrides),
    )
