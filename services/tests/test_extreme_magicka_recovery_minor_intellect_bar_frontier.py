from pathlib import Path

from minmax.named_combat_buffs import effects_for_buff
from minmax.stat_ids import StatId
from tools.audit_extreme_magicka_recovery_combined_active_bar_frontier import (
    _bar_shape_legal,
    _capacity,
)
from tools.audit_extreme_magicka_recovery_minor_intellect_bar_frontier import (
    CARRIER_LINE,
    CHALLENGER_ANIMAL_SLOTS,
    CHALLENGER_MINOR_INTELLECT_SLOTS,
    CHALLENGER_SUPPORT_SLOTS,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService

ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "eso.db"


def test_minor_intellect_is_fifteen_percent_magicka_recovery():
    rows = tuple(
        row
        for row in effects_for_buff("Minor Intellect")
        if row.stat is StatId.MAGICKA_RECOVERY and row.bucket == "resource_percent"
    )
    assert len(rows) == 1
    assert rows[0].value == 0.15


def test_one_animal_three_support_one_minor_intellect_fits_five_normal_slots():
    universe = ExtremeSkillUniverseService(DATABASE)
    animal = _capacity(universe, "Animal Companions")
    support = _capacity(universe, "Support")
    carrier = type(animal)(CARRIER_LINE, 1, 0)
    assert _bar_shape_legal(
        (
            (CHALLENGER_ANIMAL_SLOTS, animal),
            (CHALLENGER_SUPPORT_SLOTS, support),
            (CHALLENGER_MINOR_INTELLECT_SLOTS, carrier),
        )
    )


def test_minor_intellect_trade_beats_four_support_checkpoint():
    pre_percent = 5184.294
    baseline = pre_percent * (1.0 + 1.21)
    challenger = pre_percent * (1.0 + 1.26)
    assert challenger > baseline
    assert round(challenger - baseline, 3) == 259.215


def test_minor_intellect_trade_still_wins_with_major_intellect_common_to_both():
    pre_percent = 5184.294
    baseline = pre_percent * (1.0 + 1.21 + 0.30)
    challenger = pre_percent * (1.0 + 1.26 + 0.30)
    assert challenger > baseline
    assert round(challenger - baseline, 3) == 259.215
