from __future__ import annotations

"""Keep button iconography on the Foundry SVG system.

A few older UI layers used Unicode symbols as pseudo-icons. On Windows these
characters can be rendered by fallback fonts and look visually unrelated to the
Foundry line-art SVG set. They can also appear beside a real QIcon, producing a
'double icon' effect.

This compatibility layer is deliberately conservative. It removes only the
legacy technical ornaments that do not match the current visual language, and
routes all real icons through the theme-aware semantic icon loader.
"""

import re

from PySide6.QtCore import QEvent, QObject, QSize
from PySide6.QtWidgets import QApplication, QPushButton

from ui.ux_icons import icon as themed_icon

_INSTALLED = False

_ALWAYS_STRIP = {"⚒", "⚙"}
_ICON_REDUNDANT = {"⚒", "⚙", "⌘", "▣", "▤", "▧", "♢", "⌁", "ⓘ", "↺", "⟳"}
_PREFIX_RE = re.compile(r"^\s*([^\w\s])\s+")


def _strip_legacy_prefix(button: QPushButton) -> None:
    text = button.text()
    match = _PREFIX_RE.match(text)
    if not match:
        return
    symbol = match.group(1)
    has_real_icon = not button.icon().isNull()
    if symbol in _ALWAYS_STRIP or (has_real_icon and symbol in _ICON_REDUNDANT):
        button.setText(text[match.end():].lstrip())


def _apply_settings_icons(button: QPushButton) -> None:
    """Use the theme-aware SVG library for common Settings controls."""
    label = button.text().strip()
    mapping = {
        "General": "settings",
        "Integrations": "gears",
        "Archive": "archive",
        "Data Management": "square-library",
        "Broadcast": "broadcast",
        "Notifications": "warning",
        "Appearance": "sparkles",
        "Advanced": "gears",
        "About & Credits": "notebook",
        "Backup Data": "archive",
        "Export Settings": "download",
        "Import Settings": "square-library",
        "Reset to Defaults": "refresh",
    }
    icon_name = mapping.get(label)
    if not icon_name:
        return
    value = themed_icon(icon_name)
    if value.isNull():
        return
    button.setIcon(value)
    button.setIconSize(QSize(16, 16))
    button.setProperty("semanticIconName", icon_name)


class _ButtonIconFilter(QObject):
    def eventFilter(self, watched, event):
        if isinstance(watched, QPushButton) and event.type() in {
            QEvent.Type.Polish,
            QEvent.Type.Show,
        }:
            _strip_legacy_prefix(watched)
        return False


def install(app: QApplication | None = None) -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    app = app or QApplication.instance()
    if app is None:
        return

    from ui.settings_page import SettingsPage

    original_build_ui = SettingsPage._build_ui
    # Older Settings layouts exposed the right-side data controls through
    # _data_management_card. Phase 10 moved progress import/export into a real
    # _data_management_page section, so this compatibility hook must be
    # optional rather than assuming the legacy method still exists.
    original_data_management = getattr(SettingsPage, "_data_management_card", None)

    def build_ui_with_foundry_icons(self):
        original_build_ui(self)
        for button in getattr(self, "_section_buttons", []):
            _strip_legacy_prefix(button)
            _apply_settings_icons(button)

    SettingsPage._build_ui = build_ui_with_foundry_icons

    if original_data_management is not None:
        def data_management_with_foundry_icons(self):
            card = original_data_management(self)
            for name in ("backup_button", "export_button", "import_button", "reset_button"):
                button = getattr(self, name, None)
                if isinstance(button, QPushButton):
                    plain = {
                        "backup_button": "Backup Data",
                        "export_button": "Export Settings",
                        "import_button": "Import Settings",
                        "reset_button": "Reset to Defaults",
                    }[name]
                    button.setText(plain)
                    _apply_settings_icons(button)
            return card

        SettingsPage._data_management_card = data_management_with_foundry_icons

    filter_obj = _ButtonIconFilter(app)
    app.installEventFilter(filter_obj)
    app._foundry_button_icon_filter = filter_obj

    _INSTALLED = True
