from minmax.healer_ability_priority import (
    HealerDemandTagPriorities,
    HealerTagPriority,
)
from minmax.healer_rotation_policy import (
    HealerRotationPolicySet,
    HealerRotationTag,
    HealerSkillPolicy,
    ResolvedHealerSkillPolicy,
)
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.healer_rotation_priority_service import HealerRotationPriorityService


def _resolved(name: str, bar: str, slot: int, *tags: HealerRotationTag):
    return ResolvedHealerSkillPolicy(
        policy=HealerSkillPolicy(
            bar=bar,
            slot=slot,
            skill_name=name,
            tags=tuple(tags),
        ),
        ability_id=slot,
    )


def _policy_set() -> HealerRotationPolicySet:
    return HealerRotationPolicySet(
        character_name="Magrat",
        build_name="DF Healer",
        policies=(
            _resolved(
                "Illustrious Healing",
                "front",
                1,
                HealerRotationTag.CRITICAL_HEALING,
                HealerRotationTag.SUSTAINED_HEALING,
            ),
            _resolved(
                "Combat Prayer",
                "front",
                2,
                HealerRotationTag.SUPPORT_MAINTENANCE,
            ),
            _resolved(
                "Energy Orb",
                "front",
                3,
                HealerRotationTag.SUSTAINED_HEALING,
                HealerRotationTag.SUPPORT_MAINTENANCE,
            ),
            _resolved(
                "Elemental Susceptibility",
                "back",
                1,
                HealerRotationTag.SUPPORT_MAINTENANCE,
            ),
        ),
    )


def _base_priorities() -> tuple[HealerTagPriority, ...]:
    return (
        HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 0),
        HealerTagPriority(HealerRotationTag.SUSTAINED_HEALING, 2),
        HealerTagPriority(HealerRotationTag.SUPPORT_MAINTENANCE, 4),
    )


def test_projects_explicit_healer_tags_into_generation_entries() -> None:
    projection = HealerRotationPriorityService().project(
        policy_set=_policy_set(),
        base_priorities=_base_priorities(),
    )

    assert [
        (entry.bar, entry.slot, entry.skill_name, entry.priority)
        for entry in projection.entries
    ] == [
        ("front", 1, "Illustrious Healing", 0),
        ("front", 3, "Energy Orb", 2),
        ("front", 2, "Combat Prayer", 4),
        ("back", 1, "Elemental Susceptibility", 4),
    ]
    assert projection.demand is None


def test_projects_exact_demand_override_into_generation_entries() -> None:
    demand = RotationDemandWindow(
        name="Burst Rescue",
        start_seconds=20.0,
        end_seconds=25.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    projection = HealerRotationPriorityService().project(
        policy_set=_policy_set(),
        base_priorities=_base_priorities(),
        demand_priorities=(
            HealerDemandTagPriorities(
                demand_name="Burst Rescue",
                priorities=(
                    HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 0),
                    HealerTagPriority(HealerRotationTag.SUSTAINED_HEALING, 1),
                    HealerTagPriority(HealerRotationTag.SUPPORT_MAINTENANCE, 7),
                ),
                reason="protect burst healing before support upkeep",
            ),
        ),
        demand=demand,
    )

    assert [
        (entry.skill_name, entry.priority)
        for entry in projection.entries
    ] == [
        ("Illustrious Healing", 0),
        ("Energy Orb", 1),
        ("Combat Prayer", 7),
        ("Elemental Susceptibility", 7),
    ]
    assert projection.demand is demand
