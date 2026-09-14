from pathlib import Path

from minmax.named_combat_buffs import effects_for_buff
from minmax.stat_ids import StatId
from services.extreme_recovery_passive_special_branch_service import (
    ExtremeRecoveryPassiveBranchKind,
    ExtremeRecoveryPassiveSpecialBranchService,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "eso.db"
PRE_PERCENT = 5184.294
STANDING_PERCENT = 126.0


def _named_percent(name: str) -> float:
    rows = [
        row
        for row in effects_for_buff(name)
        if row.stat is StatId.MAGICKA_RECOVERY and row.bucket == "resource_percent"
    ]
    assert len(rows) == 1
    return float(rows[0].value) * 100.0


def _branch(name: str):
    universe = ExtremeSkillUniverseService(DATABASE)
    rows = [row for row in universe.passives() if row.name.strip().casefold() == name.casefold()]
    assert len(rows) == 1
    branch = ExtremeRecoveryPassiveSpecialBranchService.classify(rows[0], "magicka_recovery")
    assert branch is not None
    return branch


def test_final_contextual_percent_sources_are_canonical():
    assert _named_percent("Minor Intellect") == 15.0
    assert _named_percent("Major Intellect") == 30.0

    continuous = _branch("Continuous Attack")
    domination = _branch("Domination")
    assert continuous.kind is ExtremeRecoveryPassiveBranchKind.CONDITIONAL_PERCENT
    assert continuous.percent_ceiling == 20.0
    assert domination.kind is ExtremeRecoveryPassiveBranchKind.CONDITIONAL_PERCENT
    assert domination.percent_ceiling == 100.0


def test_final_theoretical_recovery_snapshot_is_19492_945():
    total_percent = STANDING_PERCENT + 30.0 + 20.0 + 100.0
    final_value = PRE_PERCENT * (1.0 + total_percent / 100.0)
    assert round(total_percent, 3) == 276.0
    assert round(final_value, 3) == 19492.945
