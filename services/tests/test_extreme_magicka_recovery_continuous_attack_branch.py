from pathlib import Path

from services.extreme_recovery_passive_special_branch_service import (
    ExtremeRecoveryPassiveBranchKind,
    ExtremeRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "eso.db"


def _continuous_attack():
    rows = [
        row
        for row in ExtremeSkillUniverseService(DATABASE).passives()
        if row.name.strip().casefold() == "continuous attack"
    ]
    assert rows, "Continuous Attack passive missing from canonical skill universe"
    return rows[0]


def test_continuous_attack_is_conditional_twenty_percent_magicka_recovery():
    branch = ExtremeRecoveryPassiveSpecialBranchService.classify(
        _continuous_attack(),
        "magicka_recovery",
    )

    assert branch is not None
    assert branch.kind is ExtremeRecoveryPassiveBranchKind.CONDITIONAL_PERCENT
    assert branch.can_raise_self is True
    assert branch.percent_ceiling == 20.0
    assert branch.condition == "runtime_condition_required"


def test_continuous_attack_is_not_flattened_into_static_recovery():
    branch = ExtremeRecoveryPassiveSpecialBranchService.classify(
        _continuous_attack(),
        "magicka_recovery",
    )

    assert branch is not None
    assert branch.kind is not ExtremeRecoveryPassiveBranchKind.STATIC_PERCENT
