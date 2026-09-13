from __future__ import annotations

"""Expand Coverage with the raid-facing group buff/debuff reference catalog.

The existing saved-build capability audit remains authoritative. Newly displayed
reference effects are deliberately left Unverified until canonical capability mapping
exists; this support layer does not infer combat evidence from display names.
"""

from PySide6.QtWidgets import QAbstractItemView, QLabel

from services.raid_group_effect_catalog import (
    GROUP_COVERAGE_BY_NAME,
    GROUP_COVERAGE_NAMES,
    GROUP_DEBUFF_NAMES,
)
from services.saved_build_capability_service import RaidCoverageSnapshot
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_INIT = None
_ORIGINAL_REFRESH = None
_ORIGINAL_SNAPSHOT_FOR_BUILDS = None


def _extend_snapshot(snapshot: RaidCoverageSnapshot) -> RaidCoverageSnapshot:
    status = {name: "unverified" for name in GROUP_COVERAGE_NAMES}
    providers = {name: [] for name in GROUP_COVERAGE_NAMES}
    conditional = {name: [] for name in GROUP_COVERAGE_NAMES}

    for name in GROUP_COVERAGE_NAMES:
        if name in snapshot.status:
            status[name] = snapshot.status[name]
        if name in snapshot.providers:
            providers[name] = list(snapshot.providers[name])
        if name in snapshot.conditional_providers:
            conditional[name] = list(snapshot.conditional_providers[name])

    return RaidCoverageSnapshot(status, providers, conditional)


def _snapshot_with_group_catalog(self, builds):
    assert _ORIGINAL_SNAPSHOT_FOR_BUILDS is not None
    return _extend_snapshot(_ORIGINAL_SNAPSHOT_FOR_BUILDS(self, builds))


def _apply_required_labels(page) -> None:
    table = getattr(page, "table", None)
    if table is None:
        return
    for row in range(table.rowCount()):
        name_item = table.item(row, 0)
        required_item = table.item(row, 2)
        if name_item is None or required_item is None:
            continue
        reference = GROUP_COVERAGE_BY_NAME.get(name_item.text().strip())
        if reference is not None:
            required_item.setText("Yes" if reference.default_required else "No")
            required_item.setToolTip(
                "Default raid coverage requirement."
                if reference.default_required
                else "Reference-visible group effect; not treated as a universal raid requirement."
            )


def _coverage_notes_card(page) -> FoundryCard | None:
    cached = getattr(page, "coverage_group_notes_card", None)
    if isinstance(cached, FoundryCard):
        return cached
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Coverage Notes":
            page.coverage_group_notes_card = card
            return card
    return None


def _selected_effect_name(page) -> str:
    table = getattr(page, "table", None)
    if table is None or not table.rowCount():
        return ""
    row = table.currentRow()
    if row < 0:
        row = 0
    item = table.item(row, 0)
    return item.text().strip() if item is not None else ""


def _refresh_source_notes(page, *_args) -> None:
    card = _coverage_notes_card(page)
    if card is None:
        return

    name = _selected_effect_name(page)
    reference = GROUP_COVERAGE_BY_NAME.get(name)
    card.clear()

    if reference is None:
        intro = QLabel(
            "Select a buff or debuff above to see reviewed examples of places a raid lead can look for a group-capable source."
        )
        intro.setWordWrap(True)
        card.addWidget(intro)
        return

    heading = QLabel(f"{reference.name} • {reference.category}")
    heading.setProperty("sidebarHeading", True)
    heading.setWordWrap(True)
    card.addWidget(heading)

    source_label = QLabel(
        "Known group-capable sources:\n" + "\n".join(
            f"• {source}" for source in reference.source_notes
        )
    )
    source_label.setWordWrap(True)
    source_label.setTextInteractionFlags(source_label.textInteractionFlags())
    card.addWidget(source_label)

    caveat = QLabel(
        "These are planning references. The Static Sources and Evidence columns still use canonical saved-build audit evidence and remain Unverified where FoundryDock has not proven the effect mapping end to end."
    )
    caveat.setWordWrap(True)
    caveat.setProperty("pageSubtitle", True)
    card.addWidget(caveat)


def _refresh_with_group_catalog(self, *args, **kwargs):
    assert _ORIGINAL_REFRESH is not None
    result = _ORIGINAL_REFRESH(self, *args, **kwargs)
    _apply_required_labels(self)
    _refresh_source_notes(self)
    return result


def _init_with_group_catalog(self, *args, **kwargs):
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, *args, **kwargs)

    utility_index = self.effect_filter.findText("Utility")
    if utility_index >= 0:
        self.effect_filter.removeItem(utility_index)

    self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    self.table.currentCellChanged.connect(lambda *_: _refresh_source_notes(self))

    _coverage_notes_card(self)
    _apply_required_labels(self)
    if self.table.rowCount() and self.table.currentRow() < 0:
        self.table.selectRow(0)
    _refresh_source_notes(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT, _ORIGINAL_REFRESH, _ORIGINAL_SNAPSHOT_FOR_BUILDS
    if _INSTALLED:
        return

    from ui import coverage_page

    # The Buffs & Debuffs tab is a reference/planning surface. Keep mechanic jobs
    # and ad-hoc utilities out of it; Magickasteal is categorized as a Debuff.
    coverage_page.CORE_COVERAGE = GROUP_COVERAGE_NAMES
    coverage_page.DEBUFFS = set(GROUP_DEBUFF_NAMES)
    coverage_page.UTILITY = set()

    CoveragePage = coverage_page.CoveragePage
    _ORIGINAL_INIT = CoveragePage.__init__
    _ORIGINAL_REFRESH = CoveragePage.refresh
    _ORIGINAL_SNAPSHOT_FOR_BUILDS = CoveragePage.snapshot_for_builds

    CoveragePage.snapshot_for_builds = _snapshot_with_group_catalog
    CoveragePage.refresh = _refresh_with_group_catalog
    CoveragePage.__init__ = _init_with_group_catalog
    _INSTALLED = True
