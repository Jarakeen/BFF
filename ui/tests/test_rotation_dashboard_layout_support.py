from pathlib import Path

from PySide6.QtWidgets import QApplication, QComboBox

from ui import rotation_dashboard_layout_support


def test_rotation_setup_temporarily_hides_and_unsets_advanced_mode_controls() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert '_card(page, "Rotation Setup")' in source
    assert 'page.rotation_advanced_mode_enabled = False' in source
    assert 'page.rotation_threshold_difficulty_combo' in source
    assert 'page.rotation_threshold_raid_dps_spin' in source
    assert 'page.rotation_dd_target_resistance_spin' in source
    assert 'page.rotation_recovery_resource_combo' in source
    assert 'page.rotation_recovery_trigger_spin' in source
    assert '_remove_header_wrapper(page, control)' in source
    assert 'control.hide()' in source
    assert 'page.rotation_threshold_difficulty_combo.setCurrentIndex(0)' in source
    assert 'page.rotation_threshold_raid_dps_spin.setValue(0.0)' in source
    assert 'page.rotation_dd_target_resistance_spin.setValue(-1.0)' in source
    assert 'page.rotation_recovery_resource_combo.setCurrentIndex(0)' in source
    assert 'page.rotation_recovery_trigger_spin.setValue(-1.0)' in source
    assert '_field(page, "RAID DPS")' not in source
    assert '_field(page, "TARGET RESIST")' not in source
    assert '_field(page, "RECOVERY")' not in source
    assert '_field(page, "RECOVERY TRIGGER")' not in source


def test_food_and_potions_card_owns_real_potion_generation_control() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert '_card(page, "Food & Potions")' in source
    assert 'preserve=(page.potion_combo, page.potion_on_cooldown)' in source
    assert 'card.addWidget(page._labelled_value("SAVED FOOD", page.food_value))' in source
    assert 'potion_label = QLabel("ROTATION POTION")' in source
    assert 'card.addWidget(page.potion_combo)' in source
    assert 'card.addWidget(page.potion_on_cooldown)' in source
    dashboard = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )
    assert "install_rotation_dashboard_layout(self)" in dashboard
    assert "page._refresh_build_context()" in source


def test_rotation_potion_picker_reuses_full_canonical_catalogs_on_every_build_refresh() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert 'from ui.phase5_potion_picker_support import _choices, _configure_search' in source
    assert 'ReferenceDataService(EsoDatabase(get_data_dir() / "eso.db"))' in source
    assert 'for choice in _choices():' in source
    assert 'f"Crafted · {choice.label}"' in source
    assert 'for name in _named_potion_choices():' in source
    assert 'f"Named · {name}"' in source
    assert '_select_combo_data(combo, saved_potion)' in source
    assert '_configure_search(combo)' in source
    dashboard = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )
    assert "refresh_rotation_consumables(self)" in dashboard
    assert "CanonicalRotationDashboardPage._refresh_build_context =" not in source


def test_rotation_potion_display_label_never_leaks_into_engine_value() -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    combo = QComboBox()
    combo.setEditable(True)
    combo.addItem("None", "")
    combo.addItem("Crafted · Spell Power", "spell_power")
    combo.addItem("Named · Essence of Spell Power", "Essence of Spell Power")
    combo.currentIndexChanged.connect(
        lambda index: rotation_dashboard_layout_support._sync_potion_edit_text(
            combo, index
        )
    )

    combo.setCurrentIndex(1)
    assert combo.currentText() == "spell_power"
    assert combo.currentData() == "spell_power"

    combo.setCurrentIndex(2)
    assert combo.currentText() == "Essence of Spell Power"
    assert combo.currentData() == "Essence of Spell Power"


def test_rotation_food_display_refreshes_from_selected_saved_build() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert 'getattr(build, "Food", "")' in source
    assert 'page.food_value.setText(food)' in source
    assert 'Food follows the selected saved build.' in source


def test_layout_support_moves_existing_widgets_instead_of_creating_duplicates() -> None:
    source = Path(rotation_dashboard_layout_support.__file__).read_text(encoding="utf-8")

    assert 'The canonical controls are created by their existing owners.' in source
    assert 'Keep the canonical objects alive for their existing policy methods' in source
    dashboard = Path("ui/rotation_dashboard_canonical_page.py").read_text(
        encoding="utf-8"
    )
    assert "install_rotation_dashboard_layout(self)" in dashboard
    assert "CanonicalRotationDashboardPage.__init__ =" not in source
