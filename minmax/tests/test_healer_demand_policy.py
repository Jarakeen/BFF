import pytest

from minmax.healer_demand_policy import (
    HealerDemandPolicy,
    assess_healer_demand_policy,
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


def _resolved(name: str, slot: int, *tags: HealerRotationTag) -> ResolvedHealerSkillPolicy:
    return ResolvedHealerSkillPolicy(
        policy=HealerSkillPolicy(
            bar="front" if slot <= 3 else "back",
            slot=slot if slot <= 3 else slot - 3,
            skill_name=name,
            tags=tags,
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
                1,
                HealerRotationTag.CRITICAL_HEALING,
                HealerRotationTag.BURST_PREPARATION,
                HealerRotationTag.SUSTAINED_HEALING,
            ),
            _resolved(
                "Illustrious Healing",
                2,
                HealerRotationTag.BURST_PREPARATION,
                HealerRotationTag.SUSTAINED_HEALING,
            ),
            _resolved(
                "Combat Prayer",
                3,
                HealerRotationTag.SUPPORT_MAINTENANCE,
            ),
            _resolved(
                "Elemental Ring",
                4,
                HealerRotationTag.DISCRETIONARY_FILLER,
            ),
        ),
    )


def test_burst_demand_can_protect_burst_setup_and_sacrifice_filler() -> None:
    demand = RotationDemandWindow(
        name="Ice Cage 1",
        start_seconds=10.0,
        end_seconds=17.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )

    assessment = assess_healer_demand_policy(
        policy_set=_policy_set(),
        demand=demand,
        demand_policy=HealerDemandPolicy(
            demand_name="Ice Cage 1",
            protected_tags=(
                HealerRotationTag.CRITICAL_HEALING,
                HealerRotationTag.BURST_PREPARATION,
            ),
            discretionary_tags=(HealerRotationTag.DISCRETIONARY_FILLER,),
        ),
    )

    assert [item.policy.skill_name for item in assessment.protected] == [
        "Budding Seeds",
        "Illustrious Healing",
    ]
    assert [item.policy.skill_name for item in assessment.discretionary] == [
        "Elemental Ring"
    ]
    assert [item.policy.skill_name for item in assessment.neutral] == ["Combat Prayer"]


def test_sustained_demand_can_use_different_protected_tags_for_same_build() -> None:
    demand = RotationDemandWindow(
        name="Bahsei Tank Bleed",
        start_seconds=0.0,
        end_seconds=180.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.SUSTAINED,
    )

    assessment = assess_healer_demand_policy(
        policy_set=_policy_set(),
        demand=demand,
        demand_policy=HealerDemandPolicy(
            demand_name="Bahsei Tank Bleed",
            protected_tags=(
                HealerRotationTag.CRITICAL_HEALING,
                HealerRotationTag.SUSTAINED_HEALING,
            ),
            discretionary_tags=(HealerRotationTag.DISCRETIONARY_FILLER,),
        ),
    )

    assert [item.policy.skill_name for item in assessment.protected] == [
        "Budding Seeds",
        "Illustrious Healing",
    ]
    assert [item.policy.skill_name for item in assessment.discretionary] == [
        "Elemental Ring"
    ]
    assert [item.policy.skill_name for item in assessment.neutral] == ["Combat Prayer"]


def test_demand_policy_rejects_action_matching_both_sides() -> None:
    demand = RotationDemandWindow(
        name="Check",
        start_seconds=1.0,
        end_seconds=2.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    policy_set = HealerRotationPolicySet(
        character_name="Magrat",
        build_name="DF Healer",
        policies=(
            _resolved(
                "Hybrid",
                1,
                HealerRotationTag.CRITICAL_HEALING,
                HealerRotationTag.DISCRETIONARY_FILLER,
            ),
        ),
    )

    with pytest.raises(ValueError, match="both protected and discretionary"):
        assess_healer_demand_policy(
            policy_set=policy_set,
            demand=demand,
            demand_policy=HealerDemandPolicy(
                demand_name="Check",
                protected_tags=(HealerRotationTag.CRITICAL_HEALING,),
                discretionary_tags=(HealerRotationTag.DISCRETIONARY_FILLER,),
            ),
        )


def test_demand_policy_requires_complete_healer_classification() -> None:
    demand = RotationDemandWindow(
        name="Check",
        start_seconds=1.0,
        end_seconds=2.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )

    with pytest.raises(ValueError, match="fully classified"):
        assess_healer_demand_policy(
            policy_set=HealerRotationPolicySet(
                character_name="Magrat",
                build_name="DF Healer",
                policies=(),
                unresolved=("missing policy",),
            ),
            demand=demand,
            demand_policy=HealerDemandPolicy(
                demand_name="Check",
                protected_tags=(HealerRotationTag.CRITICAL_HEALING,),
            ),
        )
