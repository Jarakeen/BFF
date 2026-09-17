from __future__ import annotations

"""Final Phase 14 Rotation presentation alignment.

The target mockup keeps the setup command center visually dominant, puts result
navigation underneath it, and preserves the canonical legacy builder widgets because
older refresh code still owns some labels. This layer changes presentation only; the
planner inputs and generation state remain owned by the existing Rotation page.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from ui.ux_icons import set_button_icon

_INSTALLED = False
_RESULT_NAV = (
    (1, "Timeline", "hourglass"),
    (2, "Uptime & Resources", "filter"),
    (3, "Explanations", "binoculars"),
    (4, "Compare", "scales"),
    (5, "Save & Export", "download"),
)


def _install_result_nav(page) -> None:
    tabs = page.rotation_builder_tabs
    setup = tabs.widget(0)
    layout = setup.layout() if setup is not None else None
    if layout is None or getattr(page, "phase14_result_nav", None) is not None:
        return

    nav = QFrame()
    nav.setProperty("foundryCard", True)
    nav.setObjectName("phase14RotationResultNav")
    nav.setMinimumHeight(104)
    nav.setMaximumHeight(116)
    root = QVBoxLayout(nav)
    root.setContentsMargins(6, 6, 6, 6)
    root.setSpacing(6)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(5)
    page.phase14_result_nav_buttons = {}
    for index, label, icon_name in _RESULT_NAV:
        button = QPushButton(label)
        button.setMinimumHeight(54)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setProperty("rotationResultNav", True)
        set_button_icon(button, icon_name, size=21)
        button.clicked.connect(lambda _checked=False, target=index: tabs.setCurrentIndex(target))
        page.phase14_result_nav_buttons[index] = button
        row.addWidget(button, 1)
    root.addLayout(row)

    hint = QLabel("Generate a rotation to unlock results.")
    hint.setProperty("muted", True)
    hint.setAlignment(hint.alignment())
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


def _apply_target_geometry(page) -> None:
    from ui.components.foundry_card import FoundryCard

    for card in page.findChildren(FoundryCard):
        title = str(card.title_label.text() or "").strip()
        if title in {"Rotation Intent", "Inputs & Obligations"}:
            card.setMinimumHeight(500)
            card.setMaximumHeight(565)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    # The collapsed target context is Character / Build / Trial / Boss / Difficulty.
    # Team remains editable in Edit Context and still drives Team duties.
    team_label = getattr(page, "phase14_context_value_labels", {}).get("TEAM")
    if team_label is not None and team_label.parentWidget() is not None:
        team_label.parentWidget().hide()


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui import phase14_rotation_command_center_support as command_center
    from ui import rotation_dashboard_layout_support as layout_support

    original_install = command_center.install_phase14_rotation_command_center
    original_enable = command_center._enable_result_tabs

    def enable_result_tabs_with_nav(page, enabled: bool) -> None:
        original_enable(page, enabled)
        _sync_result_nav(page, enabled)

    command_center._enable_result_tabs = enable_result_tabs_with_nav

    def install_target(page) -> None:
        if bool(getattr(page, "_phase14_rotation_command_center_installed", False)):
            return

        tabs = getattr(page, "rotation_builder_tabs", None)
        legacy_builder = tabs.widget(0) if tabs is not None and tabs.count() else None
        if legacy_builder is not None:
            # Phase 14 moves the real controls out of this widget, but older refresh
            # helpers still retain QLabel references created there. Keep the hidden
            # shell alive instead of deleteLater() invalidating those wrappers.
            try:
                legacy_builder.deleteLater = legacy_builder.hide
            except (AttributeError, TypeError):
                pass
            page._phase14_preserved_legacy_builder = legacy_builder

        original_install(page)
        _install_result_nav(page)
        _apply_target_geometry(page)

        # The target does not show a second tab strip above Builder. On the setup
        # page the result buttons live below the cards; once a result is opened,
        # reveal the canonical tab bar so navigation/back remains ordinary Qt.
        tab_bar = page.rotation_builder_tabs.tabBar()
        tab_bar.setVisible(False)

        def sync_tab_bar(index: int) -> None:
            tab_bar.setVisible(int(index) != 0)

        page.rotation_builder_tabs.currentChanged.connect(sync_tab_bar)
        _sync_result_nav(page, bool(getattr(page, "rotation_plan", None)))

    command_center.install_phase14_rotation_command_center = install_target
    # rotation_dashboard_layout_support imported the function directly, so replace
    # that bound module symbol too. Human beings invented imports, then made them
    # stateful. Naturally.
    layout_support.install_phase14_rotation_command_center = install_target
    _INSTALLED = True


__all__ = ["install"]
