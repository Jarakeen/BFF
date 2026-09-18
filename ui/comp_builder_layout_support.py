from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLayout, QTextEdit, QVBoxLayout

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

    columns = QHBoxLayout()
    columns.setContentsMargins(0, 0, 0, 0)
    columns.setSpacing(10)

    left = QVBoxLayout()
    left.setContentsMargins(0, 0, 0, 0)
    left.setSpacing(10)
    left.setAlignment(Qt.AlignmentFlag.AlignTop)

    right = QVBoxLayout()
    right.setContentsMargins(0, 0, 0, 0)
    right.setSpacing(10)
    right.setAlignment(Qt.AlignmentFlag.AlignTop)

    # LEFT: the team is the primary workspace. Keep the whole group visible, then
    # show team health immediately underneath so coverage gaps are never buried.
    matrix.title_label.setText("Team")
    matrix.setMinimumHeight(470)
    matrix.setMaximumHeight(480)
    left.addWidget(matrix, 0)

    coverage.title_label.setText("Team Health")
    coverage.setMinimumHeight(190)
    coverage.setMaximumHeight(235)
    left.addWidget(coverage, 0)

    evidence.setMinimumHeight(120)
    evidence.setMaximumHeight(150)
    for text in evidence.findChildren(QTextEdit):
        text.setMinimumHeight(72)
        text.setMaximumHeight(100)
    left.addWidget(evidence, 0)
    left.addStretch(1)

    # RIGHT: choose what the selected person should run. The catalog is supporting
    # evidence, not the page's main character, so it stays compact and scrollable.
    actions.setMinimumHeight(170)
    actions.setMaximumHeight(195)
    right.addWidget(actions, 0)

    details.title_label.setText("Selected Player / Build Recommendation")
    details.setMinimumHeight(440)
    details.setMaximumHeight(620)
    right.addWidget(details, 0)
    right.addStretch(1)

    columns.addLayout(left, 1)
    columns.addLayout(right, 1)
    columns.setStretch(0, 1)
    columns.setStretch(1, 1)
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
