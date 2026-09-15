from __future__ import annotations

"""Keep Rotation controls beside the concepts they configure.

The canonical controls are created by their existing owners. This layer moves
those exact widgets after page construction so canonical Generate keeps reading
the same objects and values rather than a presentation-layer copy. It also keeps
Rotation consumables synchronized with the selected saved build while using the
same canonical crafted/named potion catalogs as the Build Editor.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel

from engine.config import get_data_dir
from services.eso_database import EsoDatabase
from services.reference_data_service import ReferenceDataService
from ui.components.foundry_card import FoundryCard
from ui.phase5_potion_picker_support import _choices, _configure_search


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
        widget = item.widget()
        nested = item.layout()
        if nested is not None:
            _clear_layout(nested, preserve=keep)
        if widget is not None and widget not in keep:
            widget.deleteLater()


def _remove_header_wrapper(page, control) -> None:
    wrapper = control.parentWidget()
    if wrapper is None:
        return
    layout = getattr(page.header, "context_layout", None)
    if layout is None:
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
        page.rotation_threshold_raid_dps_spin,
        page.rotation_dd_target_resistance_spin,
        page.rotation_recovery_resource_combo,
        page.rotation_recovery_trigger_spin,
    )

    # Raid DPS / target resistance / recovery were installed as header context
    # fields. Move the canonical widgets themselves, not clones.
    for control in (
        page.rotation_threshold_raid_dps_spin,
        page.rotation_dd_target_resistance_spin,
        page.rotation_recovery_resource_combo,
        page.rotation_recovery_trigger_spin,
    ):
        _remove_header_wrapper(page, control)

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

    grid.addWidget(_field(page, "RAID DPS"), 6, 0)
    grid.addWidget(_field(page, "TARGET RESIST"), 6, 1)
    grid.addWidget(page.rotation_threshold_raid_dps_spin, 7, 0)
    grid.addWidget(page.rotation_dd_target_resistance_spin, 7, 1)

    grid.addWidget(_field(page, "RECOVERY"), 8, 0)
    grid.addWidget(_field(page, "RECOVERY TRIGGER"), 8, 1)
    grid.addWidget(page.rotation_recovery_resource_combo, 9, 0)
    grid.addWidget(page.rotation_recovery_trigger_spin, 9, 1)

    card.addLayout(grid)


def _rebuild_consumables(page) -> None:
    card = _card(page, "Food & Potions")
    if card is None:
        return

    # The potion selector is the exact control consumed by rotation_settings()
    # and canonical_generation_request(). Food remains the selected saved build's
    # canonical food rather than becoming a presentation-only override.
    _clear_layout(card.body_layout, preserve=(page.potion_combo, page.potion_on_cooldown))
    card.setMaximumHeight(225)

    page.food_value = page._value_label()
    page.food_value.setToolTip(
        "Food saved on the selected build. Rotation generation evaluates the selected build as-is."
    )
    page.potion_value = page._value_label()  # compatibility mirror; not a second input

    card.addWidget(page._labelled_value("SAVED FOOD", page.food_value))

    potion_label = QLabel("ROTATION POTION")
    potion_label.setProperty("sidebarHeading", True)
    card.addWidget(potion_label)
    page.potion_combo.setToolTip(
        "Potion used by Generate Rotation. Search crafted effect families or named/non-crafted potions. "
        "The selected build's saved potion is selected automatically."
    )
    card.addWidget(page.potion_combo)
    page.potion_on_cooldown.setToolTip(
        "When enabled, Generate Rotation schedules the selected potion on its canonical cooldown."
    )
    card.addWidget(page.potion_on_cooldown)

    hint = QLabel(
        "Food follows the selected saved build. Potion may be changed here for this generated rotation."
    )
    hint.setWordWrap(True)
    hint.setProperty("muted", True)
    card.addWidget(hint)


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
    # Preserve a legacy/free-text build value without pretending it came from a
    # current canonical catalog.
    combo.addItem(wanted, wanted)
    combo.setCurrentIndex(combo.count() - 1)


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
        index = combo.count() - 1
        combo.setItemData(
            index,
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
        index = combo.count() - 1
        combo.setItemData(
            index,
            "Named/non-crafted potion from the canonical ESO entity catalog.",
            Qt.ItemDataRole.ToolTipRole,
        )

    _select_combo_data(combo, saved_potion)
    _configure_search(combo)
    combo.blockSignals(False)


def refresh_rotation_consumables(page) -> None:
    """Synchronize consumable controls with the selected canonical saved build."""
    _refresh_consumables(page)


def install_rotation_dashboard_layout(page) -> None:
    """Move canonical controls into their final cards without replacing methods."""
    _rebuild_rotation_setup(page)
    _rebuild_consumables(page)
    # Re-apply the selected build after replacing the consumable display labels
    # and populate the full canonical potion catalog.
    page._refresh_build_context()


__all__ = ["install_rotation_dashboard_layout", "refresh_rotation_consumables"]
