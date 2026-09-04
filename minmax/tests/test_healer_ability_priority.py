import pytest

from minmax.healer_ability_priority import (
    HealerDemandTagPriorities,
    HealerTagPriority,
    generate_healer_ability_priority_list,
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


def _resolved(
    name: str,
    bar: str,
    slot: int,
    *tags: HealerRotationTag,
) -> ResolvedHealerSkillPolicy:
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
                "Budding Seeds",
                "front",
                1,
                HealerRotationTag.BURST_PREPARATION,
                HealerRotationTag.SUSTAINED_HEALING,
            ),
            _resolved(
                "Combat Prayer",
                "front",
                3,
                HealerRotationTag.SUPPORT_MAINTENANCE,
            ),
            _resolved(
                "Illustrious Healing",
                "front",
                4,
                HealerRotationTag.CRITICAL_HEALING,
                HealerRotationTag.SUSTAINED_HEALING,
            ),
            _resolved(
                "Elemental Ring",
                "back",
                1,
                HealerRotationTag.DISCRETIONARY_FILLER,
            ),
        ),
    )


def _base_priorities() -> tuple[HealerTagPriority, ...]:
    return (
        HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 0),
        HealerTagPriority(HealerRotationTag.SUSTAINED_HEALING, 2),
        HealerTagPriority(HealerRotationTag.BURST_PREPARATION, 3),
        HealerTagPriority(HealerRotationTag.SUPPORT_MAINTENANCE, 4),
        HealerTagPriority(HealerRotationTag.DISCRETIONARY_FILLER, 8),
    )


def test_healer_priority_generation_changes_between_ice_cage_and_sustained_healing() -> None:
    priorities = generate_healer_ability_priority_list(
        policy_set=_policy_set(),
        base_priorities=_base_priorities(),
        demand_priorities=(
            HealerDemandTagPriorities(
                demand_name="Ice Cage 1",
                priorities=(
                    HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 0),
                    HealerTagPriority(HealerRotationTag.BURST_PREPARATION, 1),
                    HealerTagPriority(HealerRotationTag.SUSTAINED_HEALING, 3),
                    HealerTagPriority(HealerRotationTag.SUPPORT_MAINTENANCE, 5),
                ),
                reason="paired burst rescue window",
            ),
            HealerDemandTagPriorities(
                demand_name="Bahsei Tank Bleed",
                priorities=(
                    HealerTagPriority(HealerRotationTag.SUSTAINED_HEALING, 0),
                    HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 1),
                    HealerTagPriority(HealerRotationTag.SUPPORT_MAINTENANCE, 4),
                ),
                reason="continuous tank healing pressure",
            ),
        ),
    )

    base = priorities.resolve()
    assert [(item.entry.skill_name, item.effective_priority) for item in base] == [
        ("Illustrious Healing", 0),
        ("Budding Seeds", 2),
        ("Combat Prayer", 4),
        ("Elemental Ring", 8),
    ]

    ice_cage = RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    assert [(item.entry.skill_name, item.effective_priority) for item in priorities.resolve(ice_cage)] == [
        ("Illustrious Healing", 0),
        ("Budding Seeds", 1),
        ("Combat Prayer", 5),
        ("Elemental Ring", 8),
    ]

    bahsei = RotationDemandWindow(
        name="Bahsei Tank Bleed",
        start_seconds=0.0,
        end_seconds=180.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.SUSTAINED,
    )
    assert [(item.entry.skill_name, item.effective_priority) for item in priorities.resolve(bahsei)] == [
        ("Budding Seeds", 0),
        ("Illustrious Healing", 0),
        ("Combat Prayer", 4),
        ("Elemental Ring", 8),
    ]


def test_multi_tag_skill_uses_highest_explicit_urgency() -> None:
    priorities = generate_healer_ability_priority_list(
        policy_set=_policy_set(),
        base_priorities=_base_priorities(),
    )

    budding = next(
        item for item in priorities.resolve() if item.entry.skill_name == "Budding Seeds"
    )
    assert budding.effective_priority == 2


def test_generation_rejects_missing_base_tag_coverage() -> None:
    with pytest.raises(ValueError, match="no matching tag priority"):
        generate_healer_ability_priority_list(
            policy_set=_policy_set(),
            base_priorities=(
                HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 0),
            ),
        )


def test_generation_rejects_unresolved_healer_policy() -> None:
    policy_set = HealerRotationPolicySet(
        character_name="Magrat",
        build_name="DF Healer",
        policies=_policy_set().policies,
        unresolved=("back slot 6 Aggressive Horn: healer rotation policy is required",),
    )

    with pytest.raises(ValueError, match="fully classified"):
        generate_healer_ability_priority_list(
            policy_set=policy_set,
            base_priorities=_base_priorities(),
        )
