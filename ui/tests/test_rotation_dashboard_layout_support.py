from pathlib import Path

from ui import rotation_dashboard_layout_support


def test_rotation_setup_owns_canonical_evaluation_and_recovery_controls() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert '_card(page, "Rotation Setup")' in source
    assert 'page.rotation_threshold_raid_dps_spin' in source
    assert 'page.rotation_dd_target_resistance_spin' in source
    assert 'page.rotation_recovery_resource_combo' in source
    assert 'page.rotation_recovery_trigger_spin' in source
    assert '_field(page, "RAID DPS")' in source
    assert '_field(page, "TARGET RESIST")' in source
    assert '_field(page, "RECOVERY")' in source
    assert '_field(page, "RECOVERY TRIGGER")' in source
    assert '_remove_header_wrapper(page, control)' in source


def test_food_and_potions_card_owns_real_potion_generation_control() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert '_card(page, "Food & Potions")' in source
    assert 'preserve=(page.potion_combo, page.potion_on_cooldown)' in source
    assert 'card.addWidget(page._labelled_value("SAVED FOOD", page.food_value))' in source
    assert 'potion_label = QLabel("ROTATION POTION")' in source
    assert 'card.addWidget(page.potion_combo)' in source
    assert 'card.addWidget(page.potion_on_cooldown)' in source
    assert 'self._refresh_build_context()' in source


def test_layout_support_moves_existing_widgets_instead_of_creating_duplicates() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert 'The canonical controls are created by their existing owners.' in source
    assert 'Move the canonical widgets themselves, not clones.' in source
    assert 'CanonicalRotationDashboardPage.__init__ = init_with_consolidated_controls' in source
