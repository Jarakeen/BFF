from pathlib import Path

from minmax.passive_math import (
    support_magicka_aid_recovery_percent,
    warden_flourish_recovery_percent,
)
from services.extreme_skill_universe_service import ExtremeSkillUniverseService
from tools.audit_extreme_magicka_recovery_combined_active_bar_frontier import _capacity


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "eso.db"


def test_support_line_has_five_slot_witness_capacity():
    universe = ExtremeSkillUniverseService(DATABASE)
    capacity = _capacity(universe, "Support")
    assert capacity.total >= 5


def test_one_animal_companions_slot_fully_activates_flourish():
    assert warden_flourish_recovery_percent(0) == 0.0
    assert warden_flourish_recovery_percent(1) == 0.20
    assert warden_flourish_recovery_percent(5) == 0.20


def test_five_support_slots_add_fifty_percent_recovery():
    assert support_magicka_aid_recovery_percent(5) == 0.50


def test_support_slot_has_large_direct_recovery_gain_at_torc_reference():
    # The legal Torc checkpoint has more than 5,000 pre-percent Recovery.
    # One Support slot therefore contributes >500 Recovery through Magicka Aid,
    # before any contextual percentage layers are added.
    reference = 5184.294
    direct_gain = reference * support_magicka_aid_recovery_percent(1)
    assert direct_gain > 500.0
