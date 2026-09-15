from __future__ import annotations

"""Final presentation wiring for the Rotation workspace.

The canonical controls are created by their existing owners. This layer moves those
exact widgets rather than cloning engine inputs, keeps the full potion catalog in sync,
hides the unfinished encounter-aware advanced controls, and installs the intent-first
Rotation Builder V2 workspace.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel

from engine.config import get_data_dir
from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService
from ui.components.foundry_card import FoundryCard
from ui.phase5_potion_picker_support import _choices, _configure_search
from ui.rotation_builder_v2_compact_context_support import (
    install_rotation_builder_v2_compact_context,
)
from ui.rotation_builder_v2_finish_support import install_rotation_builder_v2_finish
from ui.rotation_builder_v2_layout_support import install_rotation_builder_v2_layout


def _card(page, title: str) -> FoundryCard | None:
    wanted = str(title or "").strip().casefold()
    for card in page.findChildren(FoundryCard):
        if str(card.title_label.text() or "").strip().casefold() == wanted:
            return card
    return None


def _clear_layout(layout, *, preserve=()) -> None:
    keep = set(preserve)
    while layout.count():
        item = layout.takeAt(0)
        nested = item.layout()
        if nested is not None:
            _clear_layout(nested, preserve=keep)
        widget = item.widget()
        if widget is not None and widget not in keep:
            widget.deleteLater()


def _remove_header_wrapper(page, control) -> None:
    wrapper = control.parentWidget()
    layout = getattr(page.header, "context_layout", None)
    if wrapper is None or layout is None:
        return
    for index in range(layout.count() - 1, -1, -1):
        item = layout.itemAt(index)
        if item is not None and item.widget() is wrapper:
            layout.takeAt(index)
            wrapper.setParent(None)
            wrapper.deleteLater()
            return


def _field(page, title: str):
    return page._field_label(title)


def _disable_advanced_rotation_mode(page) -> None:
    """Hide/reset the encounter-aware controls that opt Generate into strict mode."""
    page.rotation_advanced_mode_enabled = False
    controls = (
        page.rotation_threshold_difficulty_combo,
        page.rotation_threshold_raid_dps_spin,
        page.rotation_dd_target_resistance_spin,
        page.rotation_recovery_resource_combo,
        page.rotation_recovery_trigger_spin,
    )
    for control in controls:
        _remove_header_wrapper(page, control)
        # Keep the canonical objects alive for their existing policy methods.
        control.setParent(page)
        control.hide()

    page.rotation_threshold_difficulty_combo.setCurrentIndex(0)
    page.rotation_threshold_raid_dps_spin.setValue(0.0)
    page.rotation_dd_target_resistance_spin.setValue(-1.0)
    page.rotation_recovery_resource_combo.setCurrentIndex(0)
    page.rotation_recovery_trigger_spin.setValue(-1.0)


def _rebuild_rotation_setup(page) -> None:
    card = _card(page, "Rotation Setup")
    if card is None or not card.body_layout.count():
        return

    controls = (
        page.execute_spin,
        page.rotation_type_combo,
        page.target_type_combo,
        page.ultimate_bar_combo,
        page.starting_ultimate_spin,
        page.attack_ultimate_generation,
        page.potion_combo,
        page.potion_on_cooldown,
    )
    _disable_advanced_rotation_mode(page)

    old_item = card.body_layout.takeAt(0)
    old_layout = old_item.layout() if old_item is not None else None
    if old_layout is not None:
        _clear_layout(old_layout, preserve=controls)

    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(6)
    page.rotation_setup_grid = grid
    grid.addWidget(_field(page, "EXECUTE STARTS"), 0, 0)
    grid.addWidget(_field(page, "ROTATION TYPE"), 0, 1)
    grid.addWidget(page.execute_spin, 1, 0)
    grid.addWidget(page.rotation_type_combo, 1, 1)
    grid.addWidget(_field(page, "TARGET TYPE"), 2, 0)
    grid.addWidget(_field(page, "ULTIMATE"), 2, 1)
    grid.addWidget(page.target_type_combo, 3, 0)
    grid.addWidget(page.ultimate_bar_combo, 3, 1)
    grid.addWidget(_field(page, "STARTING ULTIMATE"), 4, 0)
    grid.addWidget(page.starting_ultimate_spin, 5, 0)
    grid.addWidget(page.attack_ultimate_generation, 4, 1, 2, 1)
    card.addLayout(grid)


def _canonical_potion_value(combo, index: int | None = None) -> str:
    resolved_index = combo.currentIndex() if index is None else int(index)
    if resolved_index < 0:
        return str(combo.currentText() or "").strip()
    data = combo.itemData(resolved_index)
    return str(combo.currentText() if data is None else data or "").strip()


def _sync_potion_edit_text(combo, index: int) -> None:
    if index >= 0:
        combo.setEditText(_canonical_potion_value(combo, index))


def _named_potion_choices() -> list[str]:
    try:
        reference = ReferenceDataService(EsoDatabase(get_data_dir() / "eso.db"))
        return sorted(
            {
                str(name or "").strip()
                for name in reference.list_potion_names()
                if str(name or "").strip()
            },
            key=str.casefold,
        )
    except Exception:
        return []


def _select_combo_data(combo, value: str) -> None:
    wanted = str(value or "").strip()
    if not wanted:
        combo.setCurrentIndex(0)
        return
    for index in range(combo.count()):
        if str(combo.itemData(index) or "").strip().casefold() == wanted.casefold():
            combo.setCurrentIndex(index)
            return
    combo.addItem(wanted, wanted)
    combo.setCurrentIndex(combo.count() - 1)


def _rebuild_consumables(page) -> None:
    card = _card(page, "Food & Potions")
    if card is None:
        return
    _clear_layout(card.body_layout, preserve=(page.potion_combo, page.potion_on_cooldown))
    card.setMaximumHeight(225)

    page.food_value = page._value_label()
    page.food_value.setToolTip(
        "Food saved on the selected build. Rotation generation evaluates the selected build as-is."
    )
    page.potion_value = page._value_label()
    card.addWidget(page._labelled_value("SAVED FOOD", page.food_value))
    potion_label = QLabel("ROTATION POTION")
    potion_label.setProperty("sidebarHeading", True)
    card.addWidget(potion_label)
    card.addWidget(page.potion_combo)
    card.addWidget(page.potion_on_cooldown)

    if not bool(getattr(page, "_rotation_potion_value_sync_installed", False)):
        page.potion_combo.currentIndexChanged.connect(
            lambda index, combo=page.potion_combo: _sync_potion_edit_text(combo, index)
        )
        page._rotation_potion_value_sync_installed = True

    hint = QLabel(
        "Food follows the selected saved build. Potion may be changed here for this generated rotation."
    )
    hint.setWordWrap(True)
    hint.setProperty("muted", True)
    card.addWidget(hint)


def _refresh_consumables(page) -> None:
    build = page._selected_build()
    food = str(getattr(build, "Food", "") or "Not selected") if build is not None else "—"
    saved_potion = str(getattr(build, "Potion", "") or "").strip() if build is not None else ""
    if hasattr(page, "food_value"):
        page.food_value.setText(food)
    if hasattr(page, "potion_value"):
        page.potion_value.setText(saved_potion or "Not selected")

    combo = page.potion_combo
    combo.blockSignals(True)
    combo.clear()
    combo.addItem("None", "")
    for choice in _choices():
        combo.addItem(f"Crafted · {choice.label}", choice.canonical_id)
        combo.setItemData(
            combo.count() - 1,
            f"Crafted potion effect family · {choice.formula_count} verified reagent formula(s)",
            Qt.ItemDataRole.ToolTipRole,
        )
    crafted_ids = {
        str(combo.itemData(index) or "").strip().casefold()
        for index in range(combo.count())
        if str(combo.itemData(index) or "").strip()
    }
    for name in _named_potion_choices():
        if name.casefold() in crafted_ids:
            continue
        combo.addItem(f"Named · {name}", name)
        combo.setItemData(
            combo.count() - 1,
            "Named/non-crafted potion from the canonical ESO entity catalog.",
            Qt.ItemDataRole.ToolTipRole,
        )
    _select_combo_data(combo, saved_potion)
    _configure_search(combo)
    _sync_potion_edit_text(combo, combo.currentIndex())
    combo.blockSignals(False)


def refresh_rotation_consumables(page) -> None:
    """Synchronize consumable controls with the selected canonical saved build."""
    _refresh_consumables(page)


def install_rotation_dashboard_layout(page) -> None:
    """Install the baseline controls, then the intent-first Rotation Builder workspace."""
    _rebuild_rotation_setup(page)
    _rebuild_consumables(page)
    page._refresh_build_context()
    install_rotation_builder_v2_layout(page)
    install_rotation_builder_v2_finish(page)
    install_rotation_builder_v2_compact_context(page)


__all__ = ["install_rotation_dashboard_layout", "refresh_rotation_consumables"]
