from __future__ import annotations

from PySide6.QtWidgets import QApplication


# The global Foundry colors live in ui.foundry_theme.
# This layer intentionally handles only the card/table presentation so the
# original Foundry palette remains intact.
CARD_RULES = r"""
/* ==========================================================
   BLACK FEATHER FOUNDRY - Card / Table Presentation

   Color ownership remains in foundry_theme.py.
   ========================================================== */

/* ----------------------------------------------------------
   Cards
   ---------------------------------------------------------- */

QFrame[foundryCard="true"] {
    border-width: 2px;
    border-radius: 7px;
}

QFrame[foundryCard="true"] QWidget[cardHeader="true"] {
    min-height: 34px;
    max-height: 34px;
    border-bottom-width: 2px;
}

/* ----------------------------------------------------------
   Flush table cards

   Let the table visually become the body of the card instead
   of floating inside a second inset box.
   ---------------------------------------------------------- */

QFrame[foundryCard="true"][tableCard="true"] {
    padding: 0px;
}

QFrame[foundryCard="true"][tableCard="true"] QWidget[tableCardBody="true"] {
    margin: 0px;
    padding: 0px;
}

QFrame[foundryCard="true"][tableCard="true"] QTableWidget,
QFrame[foundryCard="true"][tableCard="true"] QTableView {
    margin: 0px;
    border: none;
    border-radius: 0px;
}

/* Keep the table header visually attached to the card header/body. */
QFrame[foundryCard="true"][tableCard="true"] QHeaderView::section {
    border-top: none;
}

/* ----------------------------------------------------------
   Scrollbars

   Keep the original Foundry scrollbar colors. Remove the
   decorative arrows so the track sits cleanly against cards.
   ---------------------------------------------------------- */

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
    height: 0px;
}
"""


def apply_foundry_palette(app: QApplication) -> None:
    """Apply card/table presentation without overriding the global palette."""
    app.setStyleSheet(app.styleSheet() + CARD_RULES)
