import pytest

from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeGearSetRecoverySpecialBranchService,
    ExtremeRecoverySpecialBranchKind,
)
from tools.audit_extreme_magicka_recovery_bastion_dominance import (
    INCUMBENT,
    REVIEWED_TOOLTIP,
    TARGET_NAME,
    TARGET_PIECES,
    bastion_optimistic_total,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import OBJECTIVE


def test_reviewed_bastion_tooltip_resolves_full_three_stack_ceiling():
    branch = ExtremeGearSetRecoverySpecialBranchService.classify(
        set_name=TARGET_NAME,
        piece_count=TARGET_PIECES,
        description=REVIEWED_TOOLTIP,
        objective_key=OBJECTIVE,
    )

    assert branch is not None
    assert branch.kind is ExtremeRecoverySpecialBranchKind.STACKED_FLAT
    assert branch.flat_ceiling == pytest.approx(318.0)
    assert branch.condition == "max_stacks"


def test_bastion_capacity_upper_bound_loses_at_reviewed_stack_ceiling():
    total = bastion_optimistic_total(structural_upper=945.0, stack_ceiling=318.0)

    assert total == pytest.approx(1263.0)
    assert INCUMBENT - total == pytest.approx(69.0)
    assert total < INCUMBENT


def test_bastion_dominance_helper_preserves_survivor_if_structural_upper_is_too_large():
    total = bastion_optimistic_total(structural_upper=1100.0, stack_ceiling=318.0)

    assert total == pytest.approx(1418.0)
    assert total > INCUMBENT
