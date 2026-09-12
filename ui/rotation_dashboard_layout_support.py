from __future__ import annotations

"""Keep Rotation controls beside the concepts they configure.

The canonical controls are created by their existing owners.  This layer only
moves those exact widgets after page construction so canonical Generate keeps
reading the same objects and values rather than a presentation-layer copy.
"""

from PySide6.QtWidgets import QGridLayout, QLabel

from ui.components.foundry_card import FoundryCard

_INSTALLED = False


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
    # and canonical_generation_request().  Food remains the saved build's food;
    # rotation generation evaluates the selected saved build rather than a fake
    # presentation-only food override.
    _clear_layout(card.body_layout, preserve=(page.potion_combo, page.potion_on_cooldown))
    card.setMaximumHeight(205)

    page.food_value = page._value_label()
    page.potion_value = page._value_label()  # compatibility mirror; not a second input

    card.addWidget(page._labelled_value("SAVED FOOD", page.food_value))

    potion_label = QLabel("ROTATION POTION")
    potion_label.setProperty("sidebarHeading", True)
    card.addWidget(potion_label)
    page.potion_combo.setToolTip(
        "Potion selection used by Generate Rotation. It initializes from the selected saved build."
    )
    card.addWidget(page.potion_combo)
    page.potion_on_cooldown.setToolTip(
        "When enabled, Generate Rotation schedules the selected potion on its canonical cooldown."
    )
    card.addWidget(page.potion_on_cooldown)

    hint = QLabel("Food follows the selected saved build; potion use is configured here for the generated rotation.")
    hint.setWordWrap(True)
    hint.setProperty("muted", True)
    card.addWidget(hint)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage

    original_init = CanonicalRotationDashboardPage.__init__

    def init_with_consolidated_controls(self, *args, **kwargs) -> None:
        original_init(self, *args, **kwargs)
        _rebuild_rotation_setup(self)
        _rebuild_consumables(self)
        # Re-apply the selected build after replacing the consumable display
        # labels.  This also initializes the real potion generation selector.
        self._refresh_build_context()

    CanonicalRotationDashboardPage.__init__ = init_with_consolidated_controls
    _INSTALLED = True


__all__ = ["install"]
