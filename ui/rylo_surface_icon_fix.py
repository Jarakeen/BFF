from __future__ import annotations

"""Final Rylo presentation enforcement.

Some legacy Grimoire layers assign leather textures and raw SVG pixmaps directly,
which bypasses the alternate-theme icon renderer and can win the Qt stylesheet
cascade. This compatibility layer deliberately installs last and only changes
presentation when the Rylo visual theme is active.
"""

import re

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QPushButton

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO

_INSTALLED = False


_RYLO_SURFACE_OVERRIDES = r"""
/* Final Rylo material override: explicitly replace Grimoire leather. */
QFrame[foundryCard="true"],
QFrame[bookPanel="true"], QWidget[bookPanel="true"] {
    background-color: #151517;
    background-image: url("@RYLO_ASSET_PATH@/rylo_stone.svg");
    border-left: 2px solid #3A3B3E;
    border-top: 2px solid #3A3B3E;
    border-right: 2px solid #202123;
    border-bottom: 2px solid #202123;
    border-radius: 1px;
}

/* Build/profile identity labels must not inherit old teal title plates. */
QFrame[foundryCard="true"] QLabel[pageTitle="true"],
QFrame[foundryCard="true"] QLabel[pageSubtitle="true"],
QLabel[pageTitle="true"], QLabel[pageSubtitle="true"] {
    background: transparent;
    background-image: none;
}

/* Final item selection override. Older Grimoire selectors used teal here. */
QListWidget::item:selected,
QTreeWidget::item:selected,
QTableWidget::item:selected,
QTableView::item:selected,
QAbstractItemView::item:selected {
    background-color: #303236;
    color: #F0ECE7;
}
QListWidget::item:selected:active,
QTreeWidget::item:selected:active,
QTableWidget::item:selected:active,
QTableView::item:selected:active,
QAbstractItemView::item:selected:active {
    background-color: #34373A;
    color: #FFFFFF;
}

/* Checked navigation must never fall back to Foundry teal/gold. */
QPushButton[nav="true"]:checked,
QPushButton[navHeader="true"]:checked,
QPushButton[navCategoryHeader="true"]:checked {
    background-color: #281719;
    color: #F0ECE7;
    border-top: 1px solid #4C3436;
    border-right: 1px solid #302326;
    border-bottom: 1px solid #302326;
    border-left: 4px solid #8B1E24;
}

/* Note/detail plates are intentionally dark and quieter than the stone cards. */
QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #171719;
    background-image: none;
    color: #D5D6D7;
    border-left: 2px solid #3B3C3F;
    border-top: 2px solid #3B3C3F;
    border-right: 2px solid #232426;
    border-bottom: 2px solid #232426;
    border-radius: 1px;
}

/* Legacy Grimoire has dedicated parchment text rules. Override those too. */
QFrame[foundryNoteCard="true"] QLabel[noteCardTitle="true"],
QWidget[foundryNoteCard="true"] QLabel[noteCardTitle="true"],
QLabel[noteCardTitle="true"] {
    background: transparent;
    color: #D9D6CF;
    font-style: normal;
}
QFrame[foundryNoteCard="true"] QLabel[noteCardBody="true"],
QWidget[foundryNoteCard="true"] QLabel[noteCardBody="true"],
QLabel[noteCardBody="true"] {
    background: transparent;
    color: #CDD0D2;
}
QFrame[foundryNoteCard="true"] QTextEdit[noteCardBody="true"],
QWidget[foundryNoteCard="true"] QTextEdit[noteCardBody="true"],
QTextEdit[noteCardBody="true"] {
    background-color: #111214;
    background-image: none;
    color: #D5D6D7;
    selection-background-color: #4A4D51;
    selection-color: #FFFFFF;
    border: 1px solid #35373A;
}

/* Some pages put the parchment property directly on labels or text widgets. */
QLabel[parchment="true"],
QTextEdit[parchment="true"],
QPlainTextEdit[parchment="true"] {
    background-color: #171719;
    background-image: none;
    color: #D5D6D7;
    border: 1px solid #35373A;
}

QWidget[cardHeader="true"] {
    background-color: rgba(27, 27, 29, 238);
    background-image: none;
    border: none;
    border-bottom: 2px solid #35363A;
}
QWidget[cardBody="true"] {
    background: transparent;
    background-image: none;
    border: none;
}
"""


def _strip_icon_canvas(svg: str) -> str:
    """Remove full-canvas tiles from the uploaded SVG icon library.

    Many source icons intentionally include a 512x512 #121416 backing path for
    standalone use. In a 16-17px UI slot that tile becomes a tiny black box and
    obscures the glyph. Rylo icons are glyph-only, so remove those canvases
    before recoloring.
    """
    svg = re.sub(
        r'<path\b(?=[^>]*\bd=["\']\s*M0\s+0\s*h512\s*v512\s*H0\s*z\s*["\'])[^>]*>\s*</path>',
        '', svg, flags=re.IGNORECASE,
    )
    svg = re.sub(
        r'<path\b(?=[^>]*\bd=["\']\s*M0\s+0\s*h512\s*v512\s*H0\s*z\s*["\'])[^>]*/>',
        '', svg, flags=re.IGNORECASE,
    )
    svg = re.sub(
        r'<rect\b(?=[^>]*(?:width=["\'](?:512|100%)["\']))(?=[^>]*(?:height=["\'](?:512|100%)["\']))[^>]*(?:/>|>\s*</rect>)',
        '', svg, flags=re.IGNORECASE,
    )
    return svg


def install(app: QApplication) -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.theme import theme_manager

    original_stylesheet_for_preferences = theme_manager.ThemeManager.stylesheet_for_preferences

    def stylesheet_with_final_rylo_surfaces(self) -> str:
        qss = original_stylesheet_for_preferences(self)
        if self.visual_theme() != VISUAL_THEME_RYLO:
            return qss
        asset_dir = get_resource_path(
            "assets", "themes", "bff", "grimoire", "assets"
        ).as_posix()
        return qss + "\n" + _RYLO_SURFACE_OVERRIDES.replace(
            "@RYLO_ASSET_PATH@", asset_dir
        )

    theme_manager.ThemeManager.stylesheet_for_preferences = stylesheet_with_final_rylo_surfaces

    # The uploaded SVG library is the canonical shape library for both visual
    # themes. Foundry renders the source gold; Rylo renders those same shapes as
    # worn steel. Override the renderer itself so no black source tile survives.
    from ui import ux_icons

    ux_icons._RYLO_DEFAULT = "#AEB3B7"
    ux_icons._RYLO_ACTIVE = "#D7D9DA"
    ux_icons._RYLO_SELECTED = "#D7D9DA"
    ux_icons._RYLO_DISABLED = "#676B70"

    original_recolor_svg = ux_icons._recolor_svg

    def recolor_svg_without_canvas(svg: str, tone: str) -> str:
        return original_recolor_svg(_strip_icon_canvas(svg), tone)

    ux_icons._recolor_svg = recolor_svg_without_canvas
    ux_icons._rylo_pixmap.cache_clear()

    # Supply every QIcon mode/state explicitly. Checked submenu buttons can ask
    # Qt for Active+On; leaving combinations absent lets Qt synthesize a result
    # that is not guaranteed to match the intended Rylo state.
    def complete_rylo_icon(path, size: int = 32) -> QIcon:
        result = QIcon()
        tones = {
            QIcon.Mode.Normal: ux_icons._RYLO_DEFAULT,
            QIcon.Mode.Active: ux_icons._RYLO_ACTIVE,
            QIcon.Mode.Selected: ux_icons._RYLO_SELECTED,
            QIcon.Mode.Disabled: ux_icons._RYLO_DISABLED,
        }
        for mode, tone in tones.items():
            for state in (QIcon.State.Off, QIcon.State.On):
                state_tone = ux_icons._RYLO_SELECTED if state == QIcon.State.On and mode != QIcon.Mode.Disabled else tone
                result.addPixmap(ux_icons._rylo_pixmap(str(path), state_tone, size), mode, state)
        return result

    ux_icons._rylo_icon = complete_rylo_icon

    # FoundryCard historically loaded source SVGs into QPixmap directly. Route
    # header icons through the theme-aware renderer so Rylo gets glyph-only
    # steel icons instead of black-backed source tiles.
    from ui.components.foundry_card import FoundryCard

    def set_icon_theme_aware(self, icon_name: str):
        self._icon_name = icon_name or ""
        self.icon_label.clear()
        self.icon_label.setVisible(bool(icon_name))
        if not icon_name:
            return

        value = ux_icons.icon(icon_name)
        if not value.isNull():
            self.icon_label.setPixmap(value.pixmap(17, 17, QIcon.Mode.Normal, QIcon.State.Off))
            self.icon_label.setToolTip(icon_name.replace("-", " ").title())
            self.icon_label.setProperty("semanticIconName", icon_name)
            return

        self.icon_label.setText(icon_name)

    FoundryCard.set_icon = set_icon_theme_aware

    # Force sidebar buttons through the corrected renderer at creation time.
    # This avoids any legacy source-QIcon assignment winning later.
    from ui.components.foundry_sidebar import FoundrySidebar

    original_leaf = FoundrySidebar.build_leaf_button
    original_category = FoundrySidebar.build_category

    def force_button_icon(button: QPushButton) -> None:
        if app.property("visualTheme") != VISUAL_THEME_RYLO:
            return
        name = button.property("semanticIconName") or ux_icons.semantic_icon(button.text())
        if not name:
            return
        path = ux_icons.icon_path(str(name))
        if path is None:
            return
        button.setIcon(complete_rylo_icon(path, 32))
        button.setProperty("semanticIconName", str(name))

    def leaf_with_rylo_icon(self, text: str, page: str, header_style: bool = False):
        button = original_leaf(self, text, page, header_style)
        force_button_icon(button)
        return button

    def category_with_rylo_icons(self, section: dict):
        wrapper = original_category(self, section)
        if app.property("visualTheme") == VISUAL_THEME_RYLO:
            for button in wrapper.findChildren(QPushButton):
                force_button_icon(button)
        return wrapper

    FoundrySidebar.build_leaf_button = leaf_with_rylo_icon
    FoundrySidebar.build_category = category_with_rylo_icons

    # The Builds identity plate is a legacy QFrame created outside FoundryCard.
    # Give it an explicit Rylo surface so the old leather-teal rule cannot win
    # through selector specificity or a stale local style.
    from ui.builds_page import BuildsPage

    original_identity_header = BuildsPage._identity_header

    def identity_header_with_rylo_surface(self, name, role, build):
        frame = original_identity_header(self, name, role, build)
        if app.property("visualTheme") == VISUAL_THEME_RYLO:
            frame.setStyleSheet(
                'QFrame { background-color: #151517; background-image: none; '
                'border: 1px solid #3A3B3E; } '
                'QLabel { background: transparent; background-image: none; } '
            )
        return frame

    BuildsPage._identity_header = identity_header_with_rylo_surface

    _INSTALLED = True
