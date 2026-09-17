from __future__ import annotations

"""Final Phase 14 Rotation presentation alignment.

The target mockup keeps the setup command center visually dominant, puts result
navigation underneath it, and preserves the canonical legacy builder widgets because
older refresh code still owns some labels. This layer changes presentation only; the
planner inputs and generation state remain owned by the existing Rotation page.
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ui.ux_icons import icon_label, refresh_theme_icons, set_button_icon

_INSTALLED = False
_RESULT_NAV = (
    (1, "Timeline", "hourglass"),
    (2, "Uptime & Resources", "filter"),
    (3, "Explanations", "binoculars"),
    (4, "Compare", "scales"),
    (5, "Save & Export", "download"),
)
_CONTEXT_LABELS = {
    "CHARACTER": "Character",
    "BUILD": "Build",
    "TEAM": "Team",
    "TRIAL": "Trial",
    "BOSS": "Boss",
    "DIFFICULTY": "Difficulty",
}


def _install_result_nav(page) -> None:
    tabs = page.rotation_builder_tabs
    setup = tabs.widget(0)
    layout = setup.layout() if setup is not None else None
    if layout is None or getattr(page, "phase14_result_nav", None) is not None:
        return

    nav = QFrame()
    nav.setProperty("foundryCard", True)
    nav.setObjectName("phase14RotationResultNav")
    nav.setMinimumHeight(112)
    nav.setMaximumHeight(124)
    root = QVBoxLayout(nav)
    root.setContentsMargins(6, 6, 6, 6)
    root.setSpacing(7)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(5)
    page.phase14_result_nav_buttons = {}
    for index, label, icon_name in _RESULT_NAV:
        button = QPushButton(label)
        button.setMinimumHeight(60)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setProperty("rotationResultNav", True)
        set_button_icon(button, icon_name, size=24)
        button.clicked.connect(lambda _checked=False, target=index: tabs.setCurrentIndex(target))
        page.phase14_result_nav_buttons[index] = button
        row.addWidget(button, 1)
    root.addLayout(row)

    hint = QLabel("Generate a rotation to unlock results.")
    hint.setProperty("muted", True)
    hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
    page.phase14_result_nav_hint = hint
    root.addWidget(hint)

    layout.addWidget(nav)
    page.phase14_result_nav = nav


def _sync_result_nav(page, enabled: bool) -> None:
    for button in getattr(page, "phase14_result_nav_buttons", {}).values():
        button.setEnabled(enabled)
    hint = getattr(page, "phase14_result_nav_hint", None)
    if hint is not None:
        hint.setText(
            "Rotation generated. Choose a result view."
            if enabled
            else "Generate a rotation to unlock results."
        )


def _polish_header(page) -> None:
    header = getattr(page, "header", None)
    if header is None:
        return
    department = getattr(header, "department", None)
    if department is not None:
        department.hide()
    star = getattr(header, "header_star", None)
    if star is not None:
        star.hide()
    save_to_build = getattr(page, "save_rotation_to_build_button", None)
    if save_to_build is not None:
        save_to_build.hide()


def _polish_context_chips(page) -> None:
    labels = getattr(page, "phase14_context_value_labels", {})
    for key, value_label in labels.items():
        if key == "TEAM":
            parent = value_label.parentWidget()
            if parent is not None:
                parent.hide()
            continue

        # showEvent runs every time the page becomes visible. The value label is
        # reparented into a caption stack during the first polish pass, so checking
        # only its current parent caused each later visit to wrap that stack again
        # and append another caption. Mark the stable value label itself instead.
        if bool(value_label.property("phase14ContextPolished")):
            continue

        chip = value_label.parentWidget()
        if chip is None:
            continue
        layout = chip.layout()
        if layout is None:
            continue
        layout.removeWidget(value_label)
        stack = QWidget()
        stack_layout = QVBoxLayout(stack)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.setSpacing(0)
        value_label.setProperty("rotationContextValue", True)
        stack_layout.addWidget(value_label)
        caption = QLabel(_CONTEXT_LABELS.get(key, key.title()))
        caption.setProperty("muted", True)
        caption.setProperty("rotationContextCaption", True)
        stack_layout.addWidget(caption)
        layout.addWidget(stack, 1)
        chip.setMinimumHeight(58)
        chip.setProperty("phase14ContextPolished", True)
        value_label.setProperty("phase14ContextPolished", True)

    edit = getattr(page, "phase14_context_edit_button", None)
    if edit is not None:
        edit.setMinimumHeight(46)
        edit.setMinimumWidth(150)
        set_button_icon(edit, "pen-tool", size=19)


def _polish_intents(page) -> None:
    for button in getattr(page, "phase14_intent_buttons", {}).values():
        button.setMinimumHeight(132)
        button.setMaximumHeight(146)
        button.setIconSize(QSize(38, 38))
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setStyleSheet(
            "QToolButton[rotationIntentChoice=\"true\"] { text-align: center; padding: 10px 14px; }"
        )


def _polish_summary_rows(page) -> None:
    for row in page.findChildren(QFrame):
        if row.property("rotationSummaryRow") is True:
            row.setMinimumHeight(56)
            row.setMaximumHeight(62)
            layout = row.layout()
            if layout is not None:
                layout.setContentsMargins(12, 7, 12, 7)


def _polish_obligations(page) -> None:
    for button in page.findChildren(QPushButton):
        if button.property("rotationObligationRow") is True:
            button.setMinimumHeight(64)
            button.setMaximumHeight(70)


def _polish_generate(page) -> None:
    button = getattr(page, "generate_button", None)
    if button is None:
        return
    button.setMinimumHeight(64)
    button.setMaximumHeight(70)
    set_button_icon(button, "rotations", size=24)
    button.setStyleSheet(
        "QPushButton { background: #C8A46A; color: #0C171B; border: 1px solid #E0C27A; "
        "border-radius: 6px; padding: 9px 16px; font-weight: 700; font-size: 16px; }"
        "QPushButton:hover { background: #D8B86F; border-color: #E8CF8C; }"
        "QPushButton:pressed { background: #B8904E; }"
        "QPushButton:disabled { background: #75684E; color: #BFC8C6; border-color: #75684E; }"
    )


def _apply_target_geometry(page) -> None:
    from ui.components.foundry_card import FoundryCard

    for card in page.findChildren(FoundryCard):
        title = str(card.title_label.text() or "").strip()
        if title == "Rotation Context":
            card.header.hide()
            card.setMinimumHeight(72)
            card.setMaximumHeight(170)
            card.set_body_margins(8, 6, 8, 6)
        elif title == "Rotation Intent":
            card.set_icon("rotations")
            card.setMinimumHeight(500)
            card.setMaximumHeight(575)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        elif title == "Inputs & Obligations":
            card.set_icon("field-office")
            card.setMinimumHeight(500)
            card.setMaximumHeight(575)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


def apply_phase14_rotation_visual_target(page) -> None:
    """Apply the target mockup after the canonical Rotation layout has been built."""
    tabs = getattr(page, "rotation_builder_tabs", None)
    if tabs is None or tabs.count() < 1:
        return

    _install_result_nav(page)
    _polish_header(page)
    _polish_context_chips(page)
    _polish_intents(page)
    _polish_summary_rows(page)
    _polish_obligations(page)
    _polish_generate(page)
    _apply_target_geometry(page)

    tab_bar = tabs.tabBar()
    tab_bar.setVisible(tabs.currentIndex() != 0)

    if not bool(getattr(page, "_phase14_result_tab_visibility_wired", False)):
        def sync_tab_bar(index: int) -> None:
            tab_bar.setVisible(int(index) != 0)

        tabs.currentChanged.connect(sync_tab_bar)
        page._phase14_result_tab_visibility_wired = True

    _sync_result_nav(page, bool(getattr(page, "rotation_plan", None)))

    # This page intentionally presents only four primary surfaces before
    # generation: Context, Rotation Intent, Inputs & Obligations, and the
    # disabled result-navigation panel. Reassert every semantic icon only after
    # those final widgets exist so local additions to assets/icons are honored.
    refresh_theme_icons(page)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import phase14_rotation_command_center_support as command_center
    from ui import rotation_dashboard_layout_support as layout_support
    from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage

    original_install = command_center.install_phase14_rotation_command_center
    original_enable = command_center._enable_result_tabs
    original_show_event = CanonicalRotationDashboardPage.showEvent

    def enable_result_tabs_with_nav(page, enabled: bool) -> None:
        original_enable(page, enabled)
        _sync_result_nav(page, enabled)

    command_center._enable_result_tabs = enable_result_tabs_with_nav

    def install_target(page) -> None:
        if bool(getattr(page, "_phase14_rotation_command_center_installed", False)):
            apply_phase14_rotation_visual_target(page)
            return

        tabs = getattr(page, "rotation_builder_tabs", None)
        legacy_builder = tabs.widget(0) if tabs is not None and tabs.count() else None
        if legacy_builder is not None:
            # Keep the old builder shell alive because older refresh helpers retain
            # QLabel references created there. Deleting it creates stale shiboken wrappers.
            try:
                legacy_builder.deleteLater = legacy_builder.hide
            except (AttributeError, TypeError):
                pass
            page._phase14_preserved_legacy_builder = legacy_builder

        original_install(page)
        apply_phase14_rotation_visual_target(page)

    def show_event_with_visual_target(self, event) -> None:
        original_show_event(self, event)
        # Reassert presentation at the real runtime boundary. This deliberately
        # avoids relying on import/monkeypatch ordering during constructor setup.
        apply_phase14_rotation_visual_target(self)

    command_center.install_phase14_rotation_command_center = install_target
    layout_support.install_phase14_rotation_command_center = install_target
    CanonicalRotationDashboardPage.showEvent = show_event_with_visual_target
    _INSTALLED = True


__all__ = ["apply_phase14_rotation_visual_target", "install"]
