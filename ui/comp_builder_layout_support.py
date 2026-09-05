from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLayout, QTextEdit

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

    # Composition Style adds one compact selector and a wrapped explanation. Grow
    # downward instead of forcing another horizontal row into the page.
    actions.setMinimumHeight(205)
    actions.setMaximumHeight(245)
    root.addWidget(actions, 0)

    matrix.setMinimumHeight(470)
    matrix.setMaximumHeight(480)
    root.addWidget(matrix, 0)

    coverage.setMinimumHeight(185)
    coverage.setMaximumHeight(235)
    root.addWidget(coverage, 0)

    details.setMinimumHeight(520)
    details.setMaximumHeight(760)
    root.addWidget(details, 0)

    evidence.setMinimumHeight(165)
    evidence.setMaximumHeight(220)
    for text in evidence.findChildren(QTextEdit):
        text.setMinimumHeight(110)
        text.setMaximumHeight(160)
    root.addWidget(evidence, 0)
    root.addStretch(1)


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
