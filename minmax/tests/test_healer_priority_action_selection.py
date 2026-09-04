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
from minmax.rotation_action_selection import (
    AbilityActionEligibility,
    select_priority_ability_action,
)
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)


def _policy_set() -> HealerRotationPolicySet:
    return HealerRotationPolicySet(
        character_name="Magrat",
        build_name="DF Healer",
        policies=(
            ResolvedHealerSkillPolicy(
                policy=HealerSkillPolicy(
                    bar="front",
                    slot=1,
                    skill_name="Budding Seeds",
                    tags=(
                        HealerRotationTag.SUSTAINED_HEALING,
                        HealerRotationTag.BURST_PREPARATION,
                    ),
                ),
                ability_id=93807,
            ),
            ResolvedHealerSkillPolicy(
                policy=HealerSkillPolicy(
                    bar="front",
                    slot=3,
                    skill_name="Combat Prayer",
                    tags=(HealerRotationTag.SUPPORT_MAINTENANCE,),
                ),
                ability_id=41189,
            ),
            ResolvedHealerSkillPolicy(
                policy=HealerSkillPolicy(
                    bar="front",
                    slot=4,
                    skill_name="Illustrious Healing",
                    tags=(HealerRotationTag.CRITICAL_HEALING,),
                ),
                ability_id=41255,
            ),
        ),
    )


def _ice_cage() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )


def _priorities():
    return generate_healer_ability_priority_list(
        policy_set=_policy_set(),
        base_priorities=(
            HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 1),
            HealerTagPriority(HealerRotationTag.BURST_PREPARATION, 3),
            HealerTagPriority(HealerRotationTag.SUSTAINED_HEALING, 4),
            HealerTagPriority(HealerRotationTag.SUPPORT_MAINTENANCE, 5),
        ),
        demand_priorities=(
            HealerDemandTagPriorities(
                demand_name="Ice Cage 1",
                priorities=(
                    HealerTagPriority(HealerRotationTag.CRITICAL_HEALING, 0),
                    HealerTagPriority(HealerRotationTag.BURST_PREPARATION, 1),
                    HealerTagPriority(HealerRotationTag.SUPPORT_MAINTENANCE, 6),
                ),
                reason="Ice Cage rescue window",
            ),
        ),
    )


def test_ice_cage_generated_priority_drives_selected_heal() -> None:
    result = select_priority_ability_action(
        priorities=_priorities(),
        current_bar="front",
        demand=_ice_cage(),
        eligibility=(
            AbilityActionEligibility("front", 1, "Budding Seeds"),
            AbilityActionEligibility("front", 3, "Combat Prayer"),
            AbilityActionEligibility("front", 4, "Illustrious Healing"),
        ),
    )

    assert result.selected is not None
    assert result.selected.priority.entry.skill_name == "Illustrious Healing"
    assert result.selected.priority.effective_priority == 0


def test_resource_safety_can_veto_nominal_ice_cage_top_priority() -> None:
    result = select_priority_ability_action(
        priorities=_priorities(),
        current_bar="front",
        demand=_ice_cage(),
        eligibility=(
            AbilityActionEligibility("front", 1, "Budding Seeds"),
            AbilityActionEligibility("front", 3, "Combat Prayer"),
            AbilityActionEligibility(
                "front",
                4,
                "Illustrious Healing",
                resource_safe=False,
                reason="would violate paired-cage reserve",
            ),
        ),
    )

    assert result.selected is not None
    assert result.selected.priority.entry.skill_name == "Budding Seeds"
    assert result.selected.priority.effective_priority == 1
    assert result.rejected[0].eligibility.reason == "would violate paired-cage reserve"
