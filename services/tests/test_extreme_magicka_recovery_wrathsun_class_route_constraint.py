from pathlib import Path

from services.extreme_recovery_class_route_frontier_service import (
    ExtremeRecoveryClassRouteFrontierService,
    _line_id,
)
from tools.audit_extreme_magicka_recovery_wrathsun_class_route_constraint import (
    ARMOR_RECOVERY_PERCENT,
    REQUIRED_LINE,
    forced_wrathsun_routes,
)

ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "eso.db"
REFERENCE = 5153.884
WILLOW_FINAL = 9259.238


def test_forced_wrathsun_routes_require_dawns_wrath_line_and_active_slot():
    service = ExtremeRecoveryClassRouteFrontierService(DATABASE)
    rows = forced_wrathsun_routes(service, reference_value=REFERENCE)

    assert rows
    for row in rows:
        assert REQUIRED_LINE in {_line_id(line) for line in row.equipped_skill_lines}
        assert dict(row.slot_counts).get(REQUIRED_LINE, 0) >= 1


def test_unconstrained_wrathsun_math_would_survive_willow_as_positive_control():
    service = ExtremeRecoveryClassRouteFrontierService(DATABASE)
    frontier = service.frontier("magicka_recovery", reference_value=REFERENCE)
    best = frontier.best_reviewed_candidate

    assert best is not None
    unconstrained_final = REFERENCE * (1.0 + ARMOR_RECOVERY_PERCENT) + best.projected_delta
    assert unconstrained_final > WILLOW_FINAL


def test_best_legal_wrathsun_class_route_loses_to_willow():
    service = ExtremeRecoveryClassRouteFrontierService(DATABASE)
    rows = forced_wrathsun_routes(service, reference_value=REFERENCE)

    assert rows
    assert rows[0].final_score < WILLOW_FINAL
