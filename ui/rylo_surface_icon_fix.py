from __future__ import annotations

"""Final Rylo presentation enforcement.

This layer installs after the Grimoire skin so legacy teal/gold widget rules,
inline build-workspace surfaces, and raw icon pixmaps cannot leak through the
Rylo theme. It also supplies Rylo-specific Raid Engine artwork while preserving
the Foundry artwork unchanged.
"""

import re

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import QApplication, QPushButton

from engine.config import get_resource_path
from services.accessibility_preferences import VISUAL_THEME_RYLO

_INSTALLED = False


_RYLO_SURFACE_OVERRIDES = r"""
/* ============================================================
   RYLO FINAL POLISH
   Warm charcoal + weathered steel + silver. Muted blue carries
   active/primary meaning; orange is danger; gold is warning/focus.
   ============================================================ */

/* Final material override: no teal card bodies. */
QFrame[foundryCard="true"],
QFrame[bookPanel="true"], QWidget[bookPanel="true"] {
    background-color: #202124;
    background-image: url("@RYLO_ASSET_PATH@/rylo_stone.svg");
    border: 1px solid #3C3E42;
    border-radius: 2px;
}
QWidget[cardHeader="true"] {
    background-color: #27282B;
    background-image: none;
    border: none;
    border-bottom: 1px solid #414347;
}
QWidget[cardBody="true"] {
    background: transparent;
    background-image: none;
    border: none;
}
QLabel[cardIcon="true"] { color: #C4C9CE; }

/* Build/profile identity labels must not inherit old teal title plates. */
QFrame[foundryCard="true"] QLabel[pageTitle="true"],
QFrame[foundryCard="true"] QLabel[pageSubtitle="true"],
QLabel[pageTitle="true"], QLabel[pageSubtitle="true"] {
    background: transparent;
    background-image: none;
}

/* Build workspace and Scribed Skills: explicitly charcoal, never Foundry teal. */
QTabWidget#buildWorkspaceTabs,
QTabWidget#buildWorkspaceTabs > QWidget,
QTabWidget#buildWorkspaceTabs QScrollArea,
QTabWidget#buildWorkspaceTabs QScrollArea > QWidget > QWidget {
    background-color: #181A1D;
    background-image: none;
}
QTabWidget#buildWorkspaceTabs::pane {
    background-color: #181A1D;
    border: 1px solid #414347;
}
QTabBar::tab {
    background-color: #252629;
    color: #AAA8A4;
    border: 1px solid #3D3F43;
    padding: 6px 11px;
}
QTabBar::tab:hover {
    background-color: #2D2F32;
    color: #E1DFDA;
}
QTabBar::tab:selected {
    background-color: #2B343D;
    color: #F0EEE9;
    border-color: #516579;
    border-bottom: 3px solid #6FA8D3;
}

/* Inputs and selectors: capabilities/build editors get neutral fields. */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit,
QPlainTextEdit, QTextEdit {
    background-color: #1A1B1E;
    background-image: none;
    color: #D9D7D2;
    selection-background-color: #36556F;
    selection-color: #FFFFFF;
    border: 1px solid #505257;
    border-radius: 2px;
}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QPlainTextEdit:hover, QTextEdit:hover { border-color: #686B70; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {
    background-color: #222326;
    border: 2px solid #C6A85B;
}
QComboBox QAbstractItemView {
    background-color: #1C1D20;
    color: #D9D7D2;
    selection-background-color: #35495B;
    selection-color: #FFFFFF;
    border: 1px solid #55585D;
}

/* Button baseline + every FoundryButton role. More-specific role rules in the
   Grimoire stylesheet used to reintroduce teal after the generic Rylo button. */
QPushButton {
    background-color: #252629;
    background-image: none;
    color: #D5D3CE;
    border: 1px solid #4C4E52;
    border-radius: 2px;
}
QPushButton:hover {
    background-color: #303135;
    border-color: #66696E;
}
QPushButton:pressed {
    background-color: #1A1B1E;
    border-color: #6F8FAA;
}
QPushButton[primary="true"] {
    background-color: #27323B;
    color: #F0EEE9;
    border: 1px solid #56738B;
    border-left: 3px solid #6FA8D3;
}
QPushButton[primary="true"]:hover {
    background-color: #30404D;
    border-color: #78A9CF;
}
QPushButton[secondary="true"] {
    background-color: #252629;
    color: #D5D3CE;
    border-color: #505257;
}
QPushButton[secondary="true"]:hover {
    background-color: #303135;
    border-color: #6A6D72;
}
QPushButton[success="true"] {
    background-color: #27323B;
    color: #EEF2F5;
    border-color: #6FA8D3;
}
QPushButton[success="true"]:hover {
    background-color: #30404D;
    border-color: #88BDE9;
}
QPushButton[warning="true"] {
    background-color: #373122;
    color: #F2E7C5;
    border-color: #C6A85B;
}
QPushButton[danger="true"], QPushButton[variant="danger"] {
    background-color: #3A2C20;
    color: #FFE2C4;
    border-color: #F28C28;
}
QPushButton[danger="true"]:hover, QPushButton[variant="danger"]:hover {
    background-color: #463326;
    border-color: #FFA44D;
}
QPushButton[ghost="true"] {
    background: transparent;
    color: #B8BCC0;
    border-color: transparent;
}
QPushButton[ghost="true"]:hover {
    background-color: #292B2E;
    color: #E1DFDA;
    border-color: #45484C;
}

/* Checked navigation: blue/silver instead of the old crimson state. */
QPushButton[nav="true"]:checked,
QPushButton[settingsNav="true"]:checked,
QPushButton[navHeader="true"]:checked,
QPushButton[navCategoryHeader="true"]:checked {
    background-color: #29333C;
    color: #F0EEE9;
    border-top: 1px solid #46545F;
    border-right: 1px solid #39434B;
    border-bottom: 1px solid #39434B;
    border-left: 4px solid #6FA8D3;
}

/* Final item selection override. */
QListWidget::item:selected,
QTreeWidget::item:selected,
QTableWidget::item:selected,
QTableView::item:selected,
QAbstractItemView::item:selected {
    background-color: #35495B;
    color: #F4F5F6;
}
QListWidget::item:selected:active,
QTreeWidget::item:selected:active,
QTableWidget::item:selected:active,
QTableView::item:selected:active,
QAbstractItemView::item:selected:active {
    background-color: #3D5367;
    color: #FFFFFF;
}

/* Note/detail plates are quieter than the main cards. */
QFrame[parchment="true"], QWidget[parchment="true"],
QFrame[foundryNoteCard="true"], QWidget[foundryNoteCard="true"] {
    background-color: #26272A;
    background-image: none;
    color: #D5D6D7;
    border: 1px solid #45474B;
    border-radius: 2px;
}
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
    background-color: #1A1B1E;
    background-image: none;
    color: #D5D6D7;
    selection-background-color: #36556F;
    selection-color: #FFFFFF;
    border: 1px solid #45474B;
}
QLabel[parchment="true"],
QTextEdit[parchment="true"],
QPlainTextEdit[parchment="true"] {
    background-color: #26272A;
    background-image: none;
    color: #D5D6D7;
    border: 1px solid #45474B;
}

/* Operations overview and build creation use the same muted blue language. */
QWidget[operationsOverview="true"] QLabel[overviewPlayerName="true"],
QWidget[operationsOverview="true"] QLabel[overviewGoalName="true"] {
    color: #B5C7D5;
}
QWidget[operationsOverview="true"] QProgressBar::chunk {
    background-color: #6F8FAA;
}
QWidget[operationsOverview="true"] QFrame[overviewAccent="teal"] {
    border-left: 3px solid #6FA8D3;
    border-radius: 1px;
}
QPushButton[newBuildAction="true"] {
    background-color: #283847;
    color: #F0ECE7;
    border: 2px solid #6FA8D3;
    border-radius: 2px;
    padding: 8px 22px;
    font-weight: 700;
}
QPushButton[newBuildAction="true"]:hover { background-color: #34495B; }
QPushButton[newBuildAction="true"]:pressed { background-color: #192733; }
QPushButton[newBuildAction="true"]:disabled {
    background-color: #24272B;
    color: #AEB3B7;
    border-color: #5A5D61;
}
QFrame#newBuildPullDown {
    border: 1px solid #5A5D61;
    border-left: 3px solid #6FA8D3;
    border-radius: 2px;
    background-color: #202124;
    background-image: none;
}
QLabel#newBuildEyebrow {
    color: #B5C7D5;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#newBuildTitle { font-size: 24px; font-weight: 700; }
"""


def _strip_icon_canvas(svg: str) -> str:
    """Remove full-canvas tiles so Rylo SVG icons remain glyph-only."""
    svg = re.sub(
        r'<path\b(?=[^>]*\bd=["\']\s*M0\s+0\s+h512\s+v512\s+H0\s+z\s*["\'])[^>]*>\s*</path>',
        '', svg, flags=re.IGNORECASE,
    )
    svg = re.sub(
        r'<path\b(?=[^>]*\bd=["\']\s*M0\s+0\s+h512\s+v512\s+H0\s+z\s*["\'])[^>]*/>',
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

    from ui import ux_icons

    ux_icons._RYLO_DEFAULT = "#C4C9CE"
    ux_icons._RYLO_ACTIVE = "#E0E3E5"
    ux_icons._RYLO_SELECTED = "#E0E3E5"
    ux_icons._RYLO_DISABLED = "#73787D"

    original_recolor_svg = ux_icons._recolor_svg

    def recolor_svg_without_canvas(svg: str, tone: str) -> str:
        return original_recolor_svg(_strip_icon_canvas(svg), tone)

    ux_icons._recolor_svg = recolor_svg_without_canvas
    ux_icons._rylo_pixmap.cache_clear()

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
                state_tone = (
                    ux_icons._RYLO_SELECTED
                    if state == QIcon.State.On and mode != QIcon.Mode.Disabled
                    else tone
                )
                result.addPixmap(
                    ux_icons._rylo_pixmap(str(path), state_tone, size),
                    mode,
                    state,
                )
        return result

    ux_icons._rylo_icon = complete_rylo_icon

    from ui.components.foundry_card import FoundryCard

    def set_icon_theme_aware(self, icon_name: str):
        self._icon_name = icon_name or ""
        self.icon_label.clear()
        self.icon_label.setVisible(bool(icon_name))
        if not icon_name:
            return
        value = ux_icons.icon(icon_name)
        if not value.isNull():
            self.icon_label.setPixmap(
                value.pixmap(17, 17, QIcon.Mode.Normal, QIcon.State.Off)
            )
            self.icon_label.setToolTip(icon_name.replace("-", " ").title())
            self.icon_label.setProperty("semanticIconName", icon_name)
            return
        self.icon_label.setText(icon_name)

    FoundryCard.set_icon = set_icon_theme_aware

    from ui.components.foundry_sidebar import FoundrySidebar

    original_leaf = FoundrySidebar.build_leaf_button
    original_category = FoundrySidebar.build_category

    def force_button_icon(button: QPushButton) -> None:
        if app.property("visualTheme") != VISUAL_THEME_RYLO:
            return
        if bool(button.property("navSubmenu")):
            button.setIcon(QIcon())
            button.setProperty("semanticIconName", "")
            return
        name = button.property("semanticIconName") or ux_icons.semantic_icon(button.text())
        if not name:
            return
        path = ux_icons.icon_path(str(name))
        if path is None:
            return
        button.setIcon(complete_rylo_icon(path, 32))
        button.setProperty("semanticIconName", str(name))

    def leaf_with_rylo_icon(
        self,
        text: str,
        page: str,
        header_style: bool = False,
        submenu: bool = False,
    ):
        button = original_leaf(self, text, page, header_style, submenu)
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

    # Build workspace used an inline Foundry teal background. Make that helper
    # theme-aware so Edit, Character Progression, and Scribed Skills all inherit
    # the same warm charcoal surface.
    from ui import build_editor_inline_compat

    original_force_dark_surface = build_editor_inline_compat._force_dark_surface

    def force_theme_dark_surface(widget) -> None:
        if app.property("visualTheme") != VISUAL_THEME_RYLO:
            original_force_dark_surface(widget)
            return
        from PySide6.QtGui import QPalette

        surface = "#181A1D"
        widget.setAutoFillBackground(True)
        palette = widget.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(surface))
        palette.setColor(QPalette.ColorRole.Base, QColor(surface))
        widget.setPalette(palette)
        widget.setStyleSheet(f"background-color: {surface};")

    build_editor_inline_compat._force_dark_surface = force_theme_dark_surface

    from widgets.build_editor import BuildEditor

    original_gear_icon = BuildEditor._gear_icon
    original_editor_identity_card = BuildEditor._build_identity_card

    slot_icons = {
        "head": "viking-helmet",
        "shoulders": "spiked-shoulder-armor",
        "chest": "leather-armor",
        "hands": "mailed-fist",
        "waist": "metal-skirt",
        "legs": "greaves",
        "feet": "metal-boot",
        "neck": "heart-necklace",
        "ring1": "ring",
        "ring2": "ring",
        "front_main_hand": "sword",
        "front_off_hand": "shield",
        "back_main_hand": "sword",
        "back_off_hand": "shield",
    }

    def gear_icon_with_rylo_svg(self, slot):
        if app.property("visualTheme") != VISUAL_THEME_RYLO:
            return original_gear_icon(self, slot)
        from PySide6.QtCore import QSize
        from PySide6.QtWidgets import QLabel

        label = QLabel()
        label.setFixedSize(22, 22)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_name = slot_icons.get(str(slot).casefold(), "builds")
        value = ux_icons.icon(icon_name)
        if not value.isNull():
            label.setPixmap(
                value.pixmap(QSize(18, 18), QIcon.Mode.Normal, QIcon.State.Off)
            )
            label.setProperty("semanticIconName", icon_name)
            label.setToolTip(icon_name.replace("-", " ").title())
        return label

    def editor_identity_card_with_rylo_details(self):
        card = original_editor_identity_card(self)
        if app.property("visualTheme") != VISUAL_THEME_RYLO:
            return card
        from PySide6.QtWidgets import QWidget

        for child in card.findChildren(QWidget):
            style = child.styleSheet()
            normalized = style.replace(" ", "").lower()
            if "rgba(200,164,106,90)" in normalized:
                child.setStyleSheet("background-color: rgba(102, 108, 114, 125);")
        return card

    BuildEditor._gear_icon = gear_icon_with_rylo_svg
    BuildEditor._build_identity_card = editor_identity_card_with_rylo_details

    from ui.builds_page import BuildsPage

    original_identity_header = BuildsPage._identity_header

    def identity_header_with_rylo_surface(self, name, role, build):
        frame = original_identity_header(self, name, role, build)
        if app.property("visualTheme") == VISUAL_THEME_RYLO:
            frame.setStyleSheet(
                'QFrame { background-color: #202124; background-image: none; '
                'border: 1px solid #414347; } '
                'QLabel { background: transparent; background-image: none; } '
            )
        return frame

    BuildsPage._identity_header = identity_header_with_rylo_surface

    # Raid Engine: use a real Rylo version of the same decorative ring/star pair
    # instead of the temporary hand-drawn circles. The live player labels and
    # chair state remain painted by the canonical widget on top of the art.
    from ui.raid_engine_dashboard_page import CompositionRingWidget, ReadinessRingWidget

    original_ring_init = CompositionRingWidget.__init__
    original_ring_paint = CompositionRingWidget.paintEvent
    original_ring_colors = CompositionRingWidget._colors

    def ring_init_with_theme_art(self, parent=None) -> None:
        original_ring_init(self, parent)
        self._bff_oval = self._oval
        self._bff_star = self._star
        oval_path = get_resource_path("assets", "decorative", "rylo_raid_engine_oval.svg")
        star_path = get_resource_path("assets", "decorative", "rylo_raid_engine_star.svg")
        self._rylo_oval = QIcon(str(oval_path)).pixmap(1000, 1000) if oval_path.exists() else self._bff_oval
        self._rylo_star = QIcon(str(star_path)).pixmap(1000, 1000) if star_path.exists() else self._bff_star

    def ring_colors_theme_aware(self):
        if app.property("visualTheme") == VISUAL_THEME_RYLO:
            return {
                "gold": QColor("#BFC5CB"),
                "teal": QColor("#6F8FAA"),
                "text": QColor("#E0DDD7"),
                "muted": QColor("#A0A4A8"),
                "tank": QColor("#6F8FAA"),
                "heal": QColor("#7A8FA5"),
                "dd": QColor("#8D9298"),
                "open": QColor("#30343A"),
                "need": QColor("#B99AE8"),
            }
        return original_ring_colors(self)

    def ring_paint_with_theme_art(self, event) -> None:
        if app.property("visualTheme") == VISUAL_THEME_RYLO:
            self._oval = self._rylo_oval
            self._star = self._rylo_star
        else:
            self._oval = self._bff_oval
            self._star = self._bff_star
        original_ring_paint(self, event)

    # The canonical painter only uses the art pair when _is_rylo() is false.
    # Palette selection no longer depends on that temporary branch; the wrapper
    # above reads the actual app theme directly.
    CompositionRingWidget.__init__ = ring_init_with_theme_art
    CompositionRingWidget._colors = ring_colors_theme_aware
    CompositionRingWidget._is_rylo = staticmethod(lambda: False)
    CompositionRingWidget.paintEvent = ring_paint_with_theme_art

    original_readiness_paint = ReadinessRingWidget.paintEvent

    def readiness_paint_theme_aware(self, event) -> None:
        if app.property("visualTheme") != VISUAL_THEME_RYLO:
            original_readiness_paint(self, event)
            return
        from PySide6.QtWidgets import QWidget
        QWidget.paintEvent(self, event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(12, 12, self.width() - 24, self.height() - 24)
        painter.setPen(QPen(QColor("#30343A"), 11))
        painter.drawArc(rect, 0, 360 * 16)
        painter.setPen(QPen(QColor("#6FA8D3"), 11))
        painter.drawArc(rect, 90 * 16, -round(360 * 16 * self.value / 100))
        painter.setPen(QColor("#D8D4CD"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(18)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.value}%")
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#A0A4A8"))
        painter.drawText(
            QRectF(0, self.height() * 0.62, self.width(), 22),
            Qt.AlignmentFlag.AlignCenter,
            "PLAN",
        )

    ReadinessRingWidget.paintEvent = readiness_paint_theme_aware

    _INSTALLED = True
