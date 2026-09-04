import pytest

from minmax.healer_rotation_policy import (
    HealerRotationTag,
    HealerSkillPolicy,
    resolve_healer_rotation_policy,
)
from minmax.rotation_duration_evidence import RotationDurationResolution
from minmax.rotation_plan import RotationActionKind
from minmax.saved_build_rotation_timing_audit import (
    SavedBuildRotationTimingAudit,
    SavedBuildSkillTimingEvidence,
)


def _skill(bar: str, slot: int, name: str, ability_id: int) -> SavedBuildSkillTimingEvidence:
    return SavedBuildSkillTimingEvidence(
        bar=bar,
        slot=slot,
        kind=RotationActionKind.ULTIMATE if slot == 6 else RotationActionKind.SKILL,
        skill_name=name,
        duration_resolution=RotationDurationResolution(
            skill_name=name,
            ability_id=ability_id,
        ),
    )


def _audit(role: str = "Healer") -> SavedBuildRotationTimingAudit:
    return SavedBuildRotationTimingAudit(
        character_name="Magrat",
        build_name="DF Healer",
        role=role,
        skills=(
            _skill("front", 1, "Budding Seeds", 93807),
            _skill("front", 3, "Combat Prayer", 41189),
            _skill("front", 4, "Illustrious Healing", 41255),
            _skill("front", 6, "Eternal Guardian", 85989),
            _skill("back", 2, "Echoing Vigor", 63247),
            _skill("back", 4, "Expansive Frost Cloak", 86129),
            _skill("back", 5, "Overflowing Altar", 43287),
            _skill("back", 6, "Aggressive Horn", 46537),
        ),
    )


def test_healer_policy_allows_multiple_role_tags_per_saved_skill() -> None:
    policy = resolve_healer_rotation_policy(
        _audit(),
        policies=(
            HealerSkillPolicy(
                bar="front",
                slot=1,
                skill_name="Budding Seeds",
                tags=(
                    HealerRotationTag.CRITICAL_HEALING,
                    HealerRotationTag.BURST_PREPARATION,
                    HealerRotationTag.SUSTAINED_HEALING,
                ),
            ),
            HealerSkillPolicy(
                bar="front",
                slot=3,
                skill_name="Combat Prayer",
                tags=(HealerRotationTag.SUPPORT_MAINTENANCE,),
            ),
            HealerSkillPolicy(
                bar="front",
                slot=4,
                skill_name="Illustrious Healing",
                tags=(
                    HealerRotationTag.BURST_PREPARATION,
                    HealerRotationTag.SUSTAINED_HEALING,
                ),
            ),
            HealerSkillPolicy(
                bar="front",
                slot=6,
                skill_name="Eternal Guardian",
                tags=(HealerRotationTag.DISCRETIONARY_FILLER,),
            ),
            HealerSkillPolicy(
                bar="back",
                slot=2,
                skill_name="Echoing Vigor",
                tags=(HealerRotationTag.SUSTAINED_HEALING,),
            ),
            HealerSkillPolicy(
                bar="back",
                slot=4,
                skill_name="Expansive Frost Cloak",
                tags=(HealerRotationTag.SUPPORT_MAINTENANCE,),
            ),
            HealerSkillPolicy(
                bar="back",
                slot=5,
                skill_name="Overflowing Altar",
                tags=(HealerRotationTag.SUPPORT_MAINTENANCE,),
            ),
            HealerSkillPolicy(
                bar="back",
                slot=6,
                skill_name="Aggressive Horn",
                tags=(
                    HealerRotationTag.SUPPORT_MAINTENANCE,
                    HealerRotationTag.BURST_PREPARATION,
                ),
            ),
        ),
    )

    assert policy.unresolved == ()
    assert [item.policy.skill_name for item in policy.with_tag(HealerRotationTag.SUSTAINED_HEALING)] == [
        "Budding Seeds",
        "Illustrious Healing",
        "Echoing Vigor",
    ]
    assert [item.policy.skill_name for item in policy.with_tag(HealerRotationTag.BURST_PREPARATION)] == [
        "Budding Seeds",
        "Illustrious Healing",
        "Aggressive Horn",
    ]


def test_healer_policy_reports_unclassified_saved_actions() -> None:
    policy = resolve_healer_rotation_policy(
        _audit(),
        policies=(
            HealerSkillPolicy(
                bar="front",
                slot=1,
                skill_name="Budding Seeds",
                tags=(HealerRotationTag.CRITICAL_HEALING,),
            ),
        ),
    )

    assert "front slot 3 Combat Prayer: healer rotation policy is required" in policy.unresolved
    assert "back slot 6 Aggressive Horn: healer rotation policy is required" in policy.unresolved


def test_healer_policy_rejects_stale_skill_binding_after_build_change() -> None:
    with pytest.raises(ValueError, match="does not match saved build"):
        resolve_healer_rotation_policy(
            _audit(),
            policies=(
                HealerSkillPolicy(
                    bar="front",
                    slot=1,
                    skill_name="Wrong Skill",
                    tags=(HealerRotationTag.CRITICAL_HEALING,),
                ),
            ),
        )


def test_healer_policy_rejects_non_healer_build() -> None:
    with pytest.raises(ValueError, match="requires a healer build"):
        resolve_healer_rotation_policy(
            _audit(role="Damage Dealer"),
            policies=(),
        )
