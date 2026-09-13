from services.extreme_health_recovery_passive_special_branch_service import (
    ExtremeHealthRecoveryPassiveBranchKind,
    ExtremeHealthRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


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


def test_elder_dragon_classifies_conditional_flat_ceiling():
    row = ExtremeHealthRecoveryPassiveSpecialBranchService.classify(
        _passive(
            "Elder Dragon",
            "Increases your Health Recovery by up to 700, based on your missing Health. Current amount: 0",
        )
    )
    assert row is not None
    assert row.kind is ExtremeHealthRecoveryPassiveBranchKind.CONDITIONAL_FLAT
    assert row.flat_ceiling == 700.0
    assert row.can_raise_self


def test_sphere_of_influence_classifies_shared_fixed_recovery():
    row = ExtremeHealthRecoveryPassiveSpecialBranchService.classify(
        _passive(
            "Sphere of Influence",
            "Casting a damage shield grants 225 Health, Magicka, and Stamina Recovery for 12 seconds.",
        )
    )
    assert row is not None
    assert row.kind is ExtremeHealthRecoveryPassiveBranchKind.CONDITIONAL_FLAT
    assert row.flat_ceiling == 225.0


def test_domination_classifies_home_keep_percent_ceiling():
    row = ExtremeHealthRecoveryPassiveSpecialBranchService.classify(
        _passive(
            "Domination",
            "Increases your Health, Magicka, and Stamina Recovery while in your campaign, depending on how many Home Keeps you own. 1 or less Keep: 50% 2 Keeps: 60% 3 Keeps: 70% 4 Keeps: 80% 5 Keeps: 90% 6 Keeps: 100%",
            domain=ExtremeSkillDomain.OTHER,
        )
    )
    assert row is not None
    assert row.kind is ExtremeHealthRecoveryPassiveBranchKind.CONDITIONAL_PERCENT
    assert row.percent_ceiling == 100.0
    assert row.condition == "home_keeps"


def test_vampire_feed_is_negative_only_for_maximize_record():
    row = ExtremeHealthRecoveryPassiveSpecialBranchService.classify(
        _passive(
            "Feed",
            "Stage 1/2/3/4 Health Recovery: -10%/-30%/-60%/-100%",
            domain=ExtremeSkillDomain.WORLD,
        )
    )
    assert row is not None
    assert row.kind is ExtremeHealthRecoveryPassiveBranchKind.NEGATIVE_ONLY
    assert not row.can_raise_self
    assert row.percent_ceiling == 100.0


def test_unreviewed_recovery_grammar_fails_closed():
    row = ExtremeHealthRecoveryPassiveSpecialBranchService.classify(
        _passive("Mystery", "Health Recovery changes according to mysterious forces.")
    )
    assert row is None
