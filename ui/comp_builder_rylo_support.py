from __future__ import annotations

from services.accessibility_preferences import VISUAL_THEME_RYLO


_INSTALLED = False


COMP_BUILDER_RYLO_QSS = r"""
/* Comp Maker: compact raid overview + selected-chair workspace. */
QTableWidget[compMakerOverview="true"] {
    background-color: #0E0F11;
    alternate-background-color: #17181A;
    border-left: 2px solid #3B3D40;
    border-top: 2px solid #3B3D40;
    border-right: 2px solid #222326;
    border-bottom: 2px solid #222326;
}
QTableWidget[compMakerOverview="true"]::item:selected {
    background-color: #2A1719;
    color: #F0ECE5;
    border-left: 2px solid #8B1E24;
}
/* Assignment mode: selected player/chair and source build share one gold cue. */
QTableWidget[compMakerOverview="true"][compAssignmentTarget="true"]::item:selected {
    background-color: #2B2418;
    color: #F2ECE2;
    border-left: 3px solid #B88A3C;
    border-top: 1px solid #4A402C;
    border-bottom: 1px solid #4A402C;
}
QFrame[compAssignmentSourceCard="true"] {
    border: 1px solid #4A402C;
}
QLabel[compAssignmentSource="true"],
QLabel[compAssignmentCue="true"] {
    background-color: #211C16;
    color: #F2ECE2;
    border-left: 3px solid #B88A3C;
    border-top: 1px solid #4A402C;
    border-right: 1px solid #302A20;
    border-bottom: 1px solid #302A20;
    padding: 7px 9px;
}
QLabel[compAssignmentCue="true"] {
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
}
QLabel[compAssignmentArrow="true"] {
    color: #D1A24D;
    background: transparent;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 800;
}
QPushButton[compAssignBuild="true"] {
    background-color: #211C16;
    color: #F2ECE2;
    border-left: 3px solid #B88A3C;
    border-top: 1px solid #4A402C;
    border-right: 1px solid #302A20;
    border-bottom: 1px solid #302A20;
    font-weight: 700;
}
QPushButton[compAssignBuild="true"]:hover {
    background-color: #2E271C;
    border-left-color: #D1A24D;
}
QWidget[compMakerChairEditor="true"],
QWidget[compMakerDetailField="true"] {
    background: transparent;
    border: none;
}
QLabel[compMakerChairTitle="true"] {
    background-color: #1A1B1D;
    color: #E1DED8;
    border-left: 4px solid #8B1E24;
    border-top: 1px solid #3D3F43;
    border-right: 1px solid #242629;
    border-bottom: 1px solid #242629;
    padding: 7px 10px;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel[compMakerConstraintLabel="true"] {
    color: #C7BBAA;
    font-family: "Bahnschrift SemiCondensed", "Arial Narrow", "Segoe UI Semibold", Arial;
    font-weight: 700;
}
QLineEdit[compMakerConstraintInput="true"] {
    background-color: #151113;
    border-left: 3px solid #8B1E24;
}
QComboBox[compCompositionStyle="true"] {
    background-color: #151113;
    color: #E1DED8;
    border-left: 3px solid #8B1E24;
    border-top: 1px solid #3D3F43;
    border-right: 1px solid #242629;
    border-bottom: 1px solid #242629;
}
QComboBox[compCompositionStyle="true"]:focus {
    border: 2px solid #B88A3C;
}
QLabel[compCompositionStyleHelp="true"],
QLabel[compInterestingStrategyHelp="true"] {
    color: #969A9E;
    background: transparent;
    padding-left: 2px;
}
QPushButton[compInterestingStrategy="true"] {
    background-color: #19171A;
    color: #E8E1D7;
    border-left: 3px solid #B88A3C;
    border-top: 1px solid #46484C;
    border-right: 1px solid #26282B;
    border-bottom: 1px solid #26282B;
    font-weight: 700;
}
QPushButton[compInterestingStrategy="true"]:hover {
    background-color: #242126;
    border-left-color: #D1A24D;
}
QFrame[compMakerChairCard="true"] QWidget[cardHeader="true"] {
    border-bottom: 2px solid #5A3336;
}
"""


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.theme import theme_manager

    original_stylesheet_for_preferences = theme_manager.ThemeManager.stylesheet_for_preferences

    def stylesheet_with_comp_builder_rylo(self) -> str:
        qss = original_stylesheet_for_preferences(self)
        if self.visual_theme() == VISUAL_THEME_RYLO:
            qss += "\n" + COMP_BUILDER_RYLO_QSS
        return qss

    theme_manager.ThemeManager.stylesheet_for_preferences = stylesheet_with_comp_builder_rylo
    _INSTALLED = True
