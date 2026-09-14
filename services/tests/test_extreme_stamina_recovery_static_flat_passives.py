import pytest

from services.extreme_recovery_passive_special_branch_service import (
    ExtremeRecoveryPassiveBranchKind,
    ExtremeRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord, ExtremeSkillDomain


def _passive(name: str, description: str, *, domain: ExtremeSkillDomain) -> ExtremePlayerSkillRecord:
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


@pytest.mark.parametrize(
    ("name", "description", "domain", "expected"),
    (
        (
            "Y'ffre's Endurance",
            "Increases your Stamina Recovery by 258.",
            ExtremeSkillDomain.RACIAL,
            258.0,
        ),
        (
            "Robustness",
            "Increases your Health, Magicka, and Stamina Recovery by 90.",
            ExtremeSkillDomain.RACIAL,
            90.0,
        ),
        (
            "Capacitor",
            "Increases your Magicka Recovery by 141 and Stamina Recovery by 141.",
            ExtremeSkillDomain.CLASS,
            141.0,
        ),
    ),
)
def test_unconditional_flat_stamina_recovery_is_static(name, description, domain, expected):
    branch = ExtremeRecoveryPassiveSpecialBranchService.classify(
        _passive(name, description, domain=domain),
        "stamina_recovery",
    )
    assert branch is not None
    assert branch.kind is ExtremeRecoveryPassiveBranchKind.STATIC_FLAT
    assert branch.flat_ceiling == pytest.approx(expected)
    assert branch.condition is None
