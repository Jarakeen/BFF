from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLayout, QTextEdit, QVBoxLayout

from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None


def _card(page, title: str) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == title:
            return card
    return None


def _card_any(page, *titles: str) -> FoundryCard | None:
    wanted = {title.strip() for title in titles}
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() in wanted:
            return card
    return None


def _detach_layout_items(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        nested = item.layout()
        if nested is not None:
            _detach_layout_items(nested)


def _install_layout(page) -> None:
    workspace_item = page.workspace_layout.itemAt(0)
    workspace = workspace_item.widget() if workspace_item is not None else None
    root = workspace.layout() if workspace is not None else None
    if root is None:
        return

    matrix = _card(page, "Composition Matrix")
    actions = _card(page, "Actions")
    details = _card_any(page, "Selected Chair Setup & Evidence", "Composition Details & Summary")
    coverage = _card(page, "Group Buff & Provider Coverage")
    evidence = _card(page, "Evidence & Provenance")
    if None in (matrix, actions, details, coverage, evidence):
        return

    _detach_layout_items(root)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(10)
    root.setAlignment(Qt.AlignmentFlag.AlignTop)

    # Main Comp Maker workspace is intentionally two columns. The left side owns
    # the player composition and its raid-wide evidence. The right side owns the
    # compact action controls and the ESO Logs / selected-chair catalog. Both
    # columns grow vertically; the page itself still forbids horizontal scrolling.
    columns = QHBoxLayout()
    columns.setContentsMargins(0, 0, 0, 0)
    columns.setSpacing(6)

    left = QVBoxLayout()
    left.setContentsMargins(0, 0, 0, 0)
    left.setSpacing(10)
    left.setAlignment(Qt.AlignmentFlag.AlignTop)

    right = QVBoxLayout()
    right.setContentsMargins(0, 0, 0, 0)
    right.setSpacing(10)
    right.setAlignment(Qt.AlignmentFlag.AlignTop)

    # LEFT: player comp -> group coverage -> evidence/provenance.
    matrix.setMinimumHeight(470)
    matrix.setMaximumHeight(480)
    left.addWidget(matrix, 0)

    coverage.setMinimumHeight(185)
    coverage.setMaximumHeight(235)
    left.addWidget(coverage, 0)

    evidence.setMinimumHeight(165)
    evidence.setMaximumHeight(220)
    for text in evidence.findChildren(QTextEdit):
        text.setMinimumHeight(110)
        text.setMaximumHeight(160)
    left.addWidget(evidence, 0)
    left.addStretch(1)

    # RIGHT: compact controls above the ESO Logs/candidate catalog.
    actions.setMinimumHeight(235)
    actions.setMaximumHeight(270)
    right.addWidget(actions, 0)

    details.title_label.setText("ESO Logs Catalog & Chair Evidence")
    details.setMinimumHeight(700)
    details.setMaximumHeight(980)
    right.addWidget(details, 1)
    right.addStretch(1)

    # The narrow center cue makes the assignment direction explicit: source build
    # on the right is assigned into the selected player/chair on the left.
    assignment_arrow = QLabel("←\nASSIGN")
    assignment_arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
    assignment_arrow.setFixedWidth(38)
    assignment_arrow.setProperty("compAssignmentArrow", True)
    assignment_arrow.setToolTip("Assign the highlighted build on the right to the selected player/chair on the left.")
    page.comp_assignment_arrow_label = assignment_arrow

    columns.addLayout(left, 1)
    columns.addWidget(assignment_arrow, 0, Qt.AlignmentFlag.AlignVCenter)
    columns.addLayout(right, 1)
    columns.setStretch(0, 1)
    columns.setStretch(1, 0)
    columns.setStretch(2, 1)
    root.addLayout(columns)
    root.addStretch(1)

    # Width stays bounded to the viewport. The matrix already hides verbose legacy
    # columns and disables its horizontal scrollbar; the page scroll remains vertical.
    page.workspace_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    page.matrix_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)


def _comp_init_with_vertical_layout(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_layout(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_vertical_layout
    _INSTALLED = True
