from __future__ import annotations

from dataclasses import dataclass

from minmax.healer_ability_priority import (
    HealerDemandTagPriorities,
    HealerTagPriority,
    generate_healer_ability_priority_list,
)
from minmax.healer_rotation_policy import HealerRotationPolicySet
from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_demand_window import RotationDemandWindow


@dataclass(frozen=True)
class HealerRotationPriorityProjection:
    """Role-specific healer policy translated into Phase 13 ability priorities.

    The healer policy layer owns semantic tags such as sustained healing or support
    maintenance. This service only projects those explicit tags into the generic
    ``AbilityPriorityEntry`` contract consumed by ``RotationGenerationSupport``.
    No skill purpose is inferred from names, bars, or slot position here.
    """

    priority_list: AbilityPriorityList
    entries: tuple[AbilityPriorityEntry, ...]
    demand: RotationDemandWindow | None = None


class HealerRotationPriorityService:
    """Bridge explicit healer policy into the role-neutral rotation generator."""

    def project(
        self,
        *,
        policy_set: HealerRotationPolicySet,
        base_priorities: tuple[HealerTagPriority, ...],
        demand_priorities: tuple[HealerDemandTagPriorities, ...] = (),
        demand: RotationDemandWindow | None = None,
    ) -> HealerRotationPriorityProjection:
        priority_list = generate_healer_ability_priority_list(
            policy_set=policy_set,
            base_priorities=base_priorities,
            demand_priorities=demand_priorities,
        )
        resolved = priority_list.resolve(demand)
        entries = tuple(
            AbilityPriorityEntry(
                bar=item.entry.bar,
                slot=item.entry.slot,
                skill_name=item.entry.skill_name,
                priority=item.effective_priority,
            )
            for item in resolved
        )
        return HealerRotationPriorityProjection(
            priority_list=priority_list,
            entries=entries,
            demand=demand,
        )
