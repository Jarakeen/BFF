from __future__ import annotations

"""Final Rylo presentation enforcement.

Some legacy Grimoire layers assign leather textures and raw SVG pixmaps directly,
which bypasses the alternate-theme icon renderer and can win the Qt stylesheet
cascade. This compatibility layer deliberately installs last and only changes
presentation when the Rylo visual theme is active.
"""

from PySide6.QtWidgets import QApplication

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
QTableView::item:selected {
    background-color: #303236;
    color: #F0ECE7;
}
QListWidget::item:selected:active,
QTreeWidget::item:selected:active,
QTableWidget::item:selected:active,
QTableView::item:selected:active {
    background-color: #34373A;
    color: #FFFFFF;
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
    # themes. Foundry renders the source gold; Rylo renders the same shapes as
    # worn steel. Never use old-gold for a selected Rylo icon, otherwise an
    # expanded/checkable navigation button quietly turns the whole rail gold.
    from ui import ux_icons

    ux_icons._RYLO_DEFAULT = "#AEB3B7"
    ux_icons._RYLO_ACTIVE = "#D7D9DA"
    ux_icons._RYLO_SELECTED = "#D7D9DA"
    ux_icons._RYLO_DISABLED = "#676B70"

    # FoundryCard historically loaded source SVGs into QPixmap directly. Route
    # header icons through the theme-aware renderer so Rylo gets matte steel.
    from ui.components.foundry_card import FoundryCard
    from ui.ux_icons import icon as themed_icon

    def set_icon_theme_aware(self, icon_name: str):
        self._icon_name = icon_name or ""
        self.icon_label.clear()
        self.icon_label.setVisible(bool(icon_name))
        if not icon_name:
            return

        value = themed_icon(icon_name)
        if not value.isNull():
            self.icon_label.setPixmap(value.pixmap(17, 17))
            self.icon_label.setToolTip(icon_name.replace("-", " ").title())
            self.icon_label.setProperty("semanticIconName", icon_name)
            return

        self.icon_label.setText(icon_name)

    FoundryCard.set_icon = set_icon_theme_aware

    _INSTALLED = True
