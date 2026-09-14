import pytest

from services.extreme_recovery_passive_special_branch_service import (
    ExtremeRecoveryPassiveBranchKind,
    ExtremeRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


def _passive(name: str, description: str, *, domain=ExtremeSkillDomain.CLASS):
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="Test Class" if domain is ExtremeSkillDomain.CLASS else "",
        skill_line="Test Line",
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=100,
        max_rank=2,
        max_rank_ability_id=200,
        description=description,
        domain=domain,
    )


def test_shared_fixed_recovery_applies_to_magicka():
    row = ExtremeRecoveryPassiveSpecialBranchService.classify(
        _passive("Sphere of Influence", "Casting a damage shield grants 225 Health, Magicka, and Stamina Recovery for 12 seconds."),
        "magicka_recovery",
    )
    assert row is not None
    assert row.kind is ExtremeRecoveryPassiveBranchKind.CONDITIONAL_FLAT
    assert row.flat_ceiling == pytest.approx(225.0)


def test_home_keep_percent_applies_to_all_recovery_objectives():
    row = ExtremeRecoveryPassiveSpecialBranchService.classify(
        _passive(
            "Domination",
            "Increases your Health, Magicka, and Stamina Recovery depending on Home Keeps. 5 Keeps: 90% 6 Keeps: 100%",
            domain=ExtremeSkillDomain.OTHER,
        ),
        "magicka_recovery",
    )
    assert row is not None
    assert row.kind is ExtremeRecoveryPassiveBranchKind.CONDITIONAL_PERCENT
    assert row.percent_ceiling == pytest.approx(100.0)


def test_static_shared_percent_accepts_health_stamina_magicka_word_order():
    row = ExtremeRecoveryPassiveSpecialBranchService.classify(
        _passive(
            "Refreshing Shadows",
            "Increases your Health, Stamina, and Magicka Recovery by |cffffff15|r%.",
        ),
        "magicka_recovery",
    )
    assert row is not None
    assert row.kind is ExtremeRecoveryPassiveBranchKind.STATIC_PERCENT
    assert row.percent_ceiling == pytest.approx(15.0)
    assert row.condition is None


def test_static_shared_percent_accepts_health_magicka_stamina_word_order():
    row = ExtremeRecoveryPassiveSpecialBranchService.classify(
        _passive(
            "Shared Recovery",
            "Increases your Health, Magicka, and Stamina Recovery by 12%.",
        ),
        "stamina_recovery",
    )
    assert row is not None
    assert row.kind is ExtremeRecoveryPassiveBranchKind.STATIC_PERCENT
    assert row.percent_ceiling == pytest.approx(12.0)


def test_static_paired_percent_accepts_magicka_and_stamina_recovery():
    passive = _passive(
        "Erudition",
        "Increases your Magicka and Stamina Recovery by 18%.",
    )
    assert ExtremeRecoveryPassiveSpecialBranchService.mentions_objective_recovery(
        passive.description,
        "magicka_recovery",
    )
    assert ExtremeRecoveryPassiveSpecialBranchService.mentions_objective_recovery(
        passive.description,
        "stamina_recovery",
    )
    assert not ExtremeRecoveryPassiveSpecialBranchService.mentions_objective_recovery(
        passive.description,
        "health_recovery",
    )
    row = ExtremeRecoveryPassiveSpecialBranchService.classify(passive, "magicka_recovery")
    assert row is not None
    assert row.kind is ExtremeRecoveryPassiveBranchKind.STATIC_PERCENT
    assert row.percent_ceiling == pytest.approx(18.0)


def test_conditional_recovery_is_increased_by_clause_preserves_flat_ceiling():
    row = ExtremeRecoveryPassiveSpecialBranchService.classify(
        _passive(
            "Undead Confederate",
            "While you have a Sacrificial Bones, SkeletalMage, or Spirit Mender active, your Health, Magicka, and Stamina Recovery is increased by 155.",
        ),
        "magicka_recovery",
    )
    assert row is not None
    assert row.kind is ExtremeRecoveryPassiveBranchKind.CONDITIONAL_FLAT
    assert row.flat_ceiling == pytest.approx(155.0)
    assert row.condition == "runtime_condition_required"


def test_slot_scaled_recovery_is_semantically_classified_without_invented_ceiling():
    row = ExtremeRecoveryPassiveSpecialBranchService.classify(
        _passive("Wellspring of the Abyss", "Increases your Health, Magicka, and Stamina Recovery by 129 for each Soldier of Apocrypha ability slotted."),
        "magicka_recovery",
    )
    assert row is not None
    assert row.kind is ExtremeRecoveryPassiveBranchKind.SCALING_RECOVERY
    assert row.flat_ceiling is None
    assert row.condition == "external_ceiling_required"


def test_health_only_vampire_penalty_does_not_poison_magicka_recovery():
    passive = _passive("Feed", "Stage 1/2/3/4 Health Recovery: -10%/-30%/-60%/-100%", domain=ExtremeSkillDomain.WORLD)
    assert ExtremeRecoveryPassiveSpecialBranchService.classify(passive, "magicka_recovery") is None


def test_unknown_objective_fails_closed():
    with pytest.raises(KeyError):
        ExtremeRecoveryPassiveSpecialBranchService.classify(
            _passive("Mystery", "Increases Magicka Recovery by 10."),
            "spell_damage",
        )
