from __future__ import annotations

from PySide6.QtWidgets import QScrollArea

from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None


def _details_card(page) -> FoundryCard | None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Composition Details & Summary":
            return card
    return None


def _move_selected_chair_before_aggregate(page) -> None:
    selected = getattr(page, "esologs_selected_chair_label", None)
    aggregate = getattr(page, "esologs_evidence_label", None)
    if selected is None or aggregate is None:
        return

    details = _details_card(page)
    if details is None:
        return

    scroll = next(iter(details.findChildren(QScrollArea)), None)
    body = scroll.widget() if scroll is not None else None
    layout = body.layout() if body is not None else None
    if layout is None:
        return

    # Remove the two ESO Logs labels from their old positions without deleting
    # them, then put the chair-specific setup first. This makes gear/skills the
    # first ESO Logs information visible when a matrix row is selected instead of
    # burying it beneath the all-chair aggregate summary.
    layout.removeWidget(selected)
    layout.removeWidget(aggregate)

    # The base Comp Builder details body starts with trial, summary, and coverage.
    # Insert immediately after those core planning fields and before the stretch.
    insert_at = min(3, layout.count())
    layout.insertWidget(insert_at, selected)
    layout.insertWidget(insert_at + 1, aggregate)


def _comp_init_with_chair_layout(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _move_selected_chair_before_aggregate(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_chair_layout
    _INSTALLED = True
