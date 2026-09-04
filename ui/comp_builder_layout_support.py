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


def _detach_layout_items(layout: QLayout) -> None:
    """Detach existing layout items without deleting their widgets."""
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
    details = _card(page, "Composition Details & Summary")
    coverage = _card(page, "Group Buff & Provider Coverage")
    evidence = _card(page, "Evidence & Provenance")
    if None in (matrix, actions, details, coverage, evidence):
        return

    _detach_layout_items(root)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(10)

    columns = QHBoxLayout()
    columns.setContentsMargins(0, 0, 0, 0)
    columns.setSpacing(10)

    left = QVBoxLayout()
    left.setContentsMargins(0, 0, 0, 0)
    left.setSpacing(10)
    left.setAlignment(Qt.AlignmentFlag.AlignTop)

    # The raid matrix is intentionally bounded to the 12-player trial group.
    matrix.setMinimumHeight(470)
    matrix.setMaximumHeight(480)
    left.addWidget(matrix, 0)

    # Coverage belongs immediately under the matrix, not after the right column
    # happens to finish growing.
    coverage.setMaximumHeight(235)
    left.addWidget(coverage, 0)
    left.addStretch(1)

    right = QVBoxLayout()
    right.setContentsMargins(0, 0, 0, 0)
    right.setSpacing(10)
    right.setAlignment(Qt.AlignmentFlag.AlignTop)

    # Keep plan actions permanently visible at the top-right.
    actions.setMinimumHeight(150)
    actions.setMaximumHeight(178)
    right.addWidget(actions, 0)

    # Details owns the flexible space and already contains its own scroll area.
    details.setMinimumHeight(300)
    details.setMaximumHeight(355)
    right.addWidget(details, 1)

    # Provenance is supporting context, so cap it instead of letting it stretch.
    evidence.setMinimumHeight(150)
    evidence.setMaximumHeight(180)
    for text in evidence.findChildren(QTextEdit):
        text.setMinimumHeight(100)
        text.setMaximumHeight(125)
    right.addWidget(evidence, 0)
    right.addStretch(1)

    columns.addLayout(left, 7)
    columns.addLayout(right, 3)
    root.addLayout(columns)


def _comp_init_with_tight_layout(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_layout(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_tight_layout
    _INSTALLED = True
