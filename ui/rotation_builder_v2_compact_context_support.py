from __future__ import annotations

"""Compact the Rotation Builder Build & Context card to the approved mockup proportions."""

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.components.foundry_card import FoundryCard


def _card(page, title: str) -> FoundryCard | None:
    wanted = str(title or "").strip().casefold()
    for card in page.findChildren(FoundryCard):
        if str(card.title_label.text() or "").strip().casefold() == wanted:
            return card
    return None


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        nested = item.layout()
        if nested is not None:
            _clear_layout(nested)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


def _compact_field(title: str, control: QWidget) -> QWidget:
    host = QWidget()
    host.setProperty("rotationCompactContextField", True)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    label = QLabel(title)
    label.setProperty("sidebarHeading", True)
    label.setMaximumHeight(16)

    control.setMinimumHeight(30)
    control.setMaximumHeight(30)

    layout.addWidget(label)
    layout.addWidget(control)
    return host


def install_rotation_builder_v2_compact_context(page) -> None:
    """Rebuild the top context card with the same shallow proportions as the mockup.

    The canonical controls themselves are reused. This only removes the redundant
    multi-line summary/help copy from this card and packs the context selectors into
    a shallow two-row layout.
    """
    if bool(getattr(page, "_rotation_compact_context_installed", False)):
        return

    card = _card(page, "Build & Context")
    if card is None:
        return

    controls = (
        page.character_combo,
        page.build_combo,
        page.rotation_team_combo,
        page.rotation_content_combo,
        page.rotation_boss_combo,
        page.rotation_threshold_difficulty_combo,
        page.rotation_goal_combo,
        page.food_value,
    )

    # Detach the live canonical widgets before removing the previous wrappers.
    for control in controls:
        control.setParent(page)

    build_summary = getattr(page, "build_summary", None)
    if build_summary is not None:
        build_summary.setParent(page)
        build_summary.hide()

    _clear_layout(card.body_layout)
    card.set_body_margins(10, 5, 10, 6)
    card.set_body_spacing(4)

    context_grid = QGridLayout()
    context_grid.setContentsMargins(0, 0, 0, 0)
    context_grid.setHorizontalSpacing(8)
    context_grid.setVerticalSpacing(3)
    for column in range(6):
        context_grid.setColumnStretch(column, 1)

    context_grid.addWidget(_compact_field("CHARACTER", page.character_combo), 0, 0)
    context_grid.addWidget(_compact_field("BUILD", page.build_combo), 0, 1)
    context_grid.addWidget(_compact_field("TEAM", page.rotation_team_combo), 0, 2)
    context_grid.addWidget(_compact_field("CONTENT", page.rotation_content_combo), 0, 3)
    context_grid.addWidget(_compact_field("BOSS", page.rotation_boss_combo), 0, 4)
    context_grid.addWidget(
        _compact_field("DIFFICULTY", page.rotation_threshold_difficulty_combo),
        0,
        5,
    )
    card.addLayout(context_grid)

    lower = QHBoxLayout()
    lower.setContentsMargins(0, 0, 0, 0)
    lower.setSpacing(8)
    lower.addWidget(_compact_field("ROTATION GOAL", page.rotation_goal_combo), 3)

    food_host = QWidget()
    food_layout = QVBoxLayout(food_host)
    food_layout.setContentsMargins(0, 0, 0, 0)
    food_layout.setSpacing(2)
    food_label = QLabel("SAVED FOOD")
    food_label.setProperty("sidebarHeading", True)
    food_label.setMaximumHeight(16)
    page.food_value.setMinimumHeight(30)
    page.food_value.setMaximumHeight(30)
    food_layout.addWidget(food_label)
    food_layout.addWidget(page.food_value)
    lower.addWidget(food_host, 2)
    lower.addStretch(1)
    card.addLayout(lower)

    page._rotation_compact_context_installed = True


__all__ = ["install_rotation_builder_v2_compact_context"]
