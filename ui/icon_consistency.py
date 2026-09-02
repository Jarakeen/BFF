from __future__ import annotations

"""Keep button iconography on the Foundry SVG system.

A few older UI layers used Unicode symbols as pseudo-icons. On Windows these
characters can be rendered by fallback fonts and look visually unrelated to the
Foundry line-art SVG set. They can also appear beside a real QIcon, producing a
'double icon' effect.

This compatibility layer is deliberately conservative. It removes only the
legacy technical ornaments that do not match the current visual language, and
lets a real QIcon take precedence when one is already present.
"""

import re

from PySide6.QtCore import QEvent, QObject, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QPushButton

from engine.config import get_resource_path

_INSTALLED = False

# Crossed tools / cog are always legacy ornament in the current UI. The other
# symbols are stripped only when a real icon is present, so thematic text such
# as the Broadcast coffee/moon controls is not touched.
_ALWAYS_STRIP = {"⚒", "⚙"}
_ICON_REDUNDANT = {"⚒", "⚙", "⌘", "▣", "▤", "▧", "♢", "⌁", "ⓘ", "↺", "⟳"}
_PREFIX_RE = re.compile(r"^\s*([^\w\s])\s+")


def _icon(name: str) -> QIcon:
    path = get_resource_path("assets", "icons", name)
    return QIcon(str(path)) if path.is_file() else QIcon()


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
    """Use the existing Foundry SVG library for common Settings controls."""
    label = button.text().strip()
    mapping = {
        "General": "settings.svg",
        "Integrations": "gears.svg",
        "Archive": "archive.svg",
        "Broadcast": "broadcast.svg",
        "Notifications": "warning.svg",
        "Appearance": "sparkles.svg",
        "Advanced": "gears.svg",
        "About & Credits": "notebook.svg",
        "Backup Data": "archive.svg",
        "Export Settings": "download.svg",
        "Import Settings": "square-library.svg",
        "Reset to Defaults": "refresh.svg",
    }
    icon_name = mapping.get(label)
    if not icon_name:
        return
    icon = _icon(icon_name)
    if icon.isNull():
        return
    button.setIcon(icon)
    button.setIconSize(QSize(16, 16))


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

    # Settings is currently the main concentration of legacy pseudo-icons.
    # Patch it before MainWindow constructs the page so users never see the
    # fallback-font version even for one frame.
    from ui.settings_page import SettingsPage

    original_build_ui = SettingsPage._build_ui
    original_data_management = SettingsPage._data_management_card

    def build_ui_with_foundry_icons(self):
        original_build_ui(self)
        for button in getattr(self, "_section_buttons", []):
            _strip_legacy_prefix(button)
            _apply_settings_icons(button)

    def data_management_with_foundry_icons(self):
        card = original_data_management(self)
        for name in ("backup_button", "export_button", "import_button", "reset_button"):
            button = getattr(self, name, None)
            if isinstance(button, QPushButton):
                # Assign the SVG first, then remove the redundant text glyph.
                plain = {
                    "backup_button": "Backup Data",
                    "export_button": "Export Settings",
                    "import_button": "Import Settings",
                    "reset_button": "Reset to Defaults",
                }[name]
                button.setText(plain)
                _apply_settings_icons(button)
        return card

    SettingsPage._build_ui = build_ui_with_foundry_icons
    SettingsPage._data_management_card = data_management_with_foundry_icons

    filter_obj = _ButtonIconFilter(app)
    app.installEventFilter(filter_obj)
    # QApplication does not own arbitrary Python references strongly enough for
    # us to rely on wrapper lifetime. Keep it explicitly for the app lifetime.
    app._foundry_button_icon_filter = filter_obj

    _INSTALLED = True
