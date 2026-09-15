from __future__ import annotations

"""Expand Coverage with raid-facing group effects and unique support-set effects.

The existing saved-build capability audit remains authoritative for canonical named
effects. The reviewed unique support-set catalog is overlaid only when exact saved-build
equipment proves the required set-piece threshold. Proc/activation effects remain
Conditional; this layer never infers uptime from gear presence.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QLabel

from services.raid_group_effect_catalog import (
    GROUP_COVERAGE_BY_NAME,
    GROUP_COVERAGE_NAMES,
    GROUP_DEBUFF_NAMES,
)
from services.raid_unique_support_set_capability_service import (
    RaidUniqueSupportSetCapabilityService,
)
from services.raid_unique_support_set_catalog import (
    UNIQUE_SUPPORT_DEBUFF_NAMES,
    UNIQUE_SUPPORT_SET_BY_NAME,
    UNIQUE_SUPPORT_SET_NAMES,
)
from services.saved_build_capability_service import RaidCoverageSnapshot
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_INIT = None
_ORIGINAL_REFRESH = None
_ORIGINAL_SNAPSHOT_FOR_BUILDS = None

# Unique-set references deliberately override duplicate planning rows so their Type
# column can explain the unnamed effect instead of merely saying Buff or Debuff.
REFERENCE_BY_NAME = {**GROUP_COVERAGE_BY_NAME, **UNIQUE_SUPPORT_SET_BY_NAME}
COVERAGE_NAMES = tuple(dict.fromkeys((*GROUP_COVERAGE_NAMES, *UNIQUE_SUPPORT_SET_NAMES)))
DEBUFF_NAMES = frozenset((*GROUP_DEBUFF_NAMES, *UNIQUE_SUPPORT_DEBUFF_NAMES))
UNIQUE_NAMES = frozenset(UNIQUE_SUPPORT_SET_NAMES)


def _extend_snapshot(snapshot: RaidCoverageSnapshot) -> RaidCoverageSnapshot:
    status = {name: "unverified" for name in COVERAGE_NAMES}
    providers = {name: [] for name in COVERAGE_NAMES}
    conditional = {name: [] for name in COVERAGE_NAMES}

    for name in COVERAGE_NAMES:
        if name in snapshot.status:
            status[name] = snapshot.status[name]
        if name in snapshot.providers:
            providers[name] = list(snapshot.providers[name])
        if name in snapshot.conditional_providers:
            conditional[name] = list(snapshot.conditional_providers[name])

    return RaidCoverageSnapshot(status, providers, conditional)


def _snapshot_with_group_catalog(self, builds):
    assert _ORIGINAL_SNAPSHOT_FOR_BUILDS is not None
    selected_builds = tuple(builds)
    snapshot = _extend_snapshot(
        _ORIGINAL_SNAPSHOT_FOR_BUILDS(self, selected_builds)
    )
    return RaidUniqueSupportSetCapabilityService().overlay(snapshot, selected_builds)


def _apply_reference_labels(page) -> None:
    table = getattr(page, "table", None)
    if table is None:
        return
    for row in range(table.rowCount()):
        name_item = table.item(row, 0)
        type_item = table.item(row, 1)
        required_item = table.item(row, 2)
        if name_item is None:
            continue
        reference = REFERENCE_BY_NAME.get(name_item.text().strip())
        if reference is None:
            continue

        if type_item is not None:
            type_item.setText(getattr(reference, "type_label", "") or reference.category)
            type_item.setToolTip(
                "Unique support-set effect; see Coverage Notes for source details."
                if getattr(reference, "type_label", "")
                else f"Group-relevant {reference.category.lower()}."
            )

        if required_item is not None:
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
    reference = REFERENCE_BY_NAME.get(name)
    card.clear()

    if reference is None:
        intro = QLabel(
            "Select a buff, debuff, or unique support-set effect above to see known sources."
        )
        intro.setWordWrap(True)
        card.addWidget(intro)
        return

    type_label = getattr(reference, "type_label", "") or reference.category
    heading = QLabel(f"{reference.name} • {type_label}")
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


def _apply_coverage_filters_with_unique(self, *_args) -> None:
    effect_type = self.effect_filter.currentText()
    query = self.search.text().strip().casefold()

    for row in range(self.table.rowCount()):
        item = self.table.item(row, 0)
        if item is None:
            continue

        name = item.text()
        evidence_item = self.table.item(row, 8)
        source_item = self.table.item(row, 3)
        evidence = (
            evidence_item.data(Qt.ItemDataRole.UserRole)
            if evidence_item is not None
            else None
        )
        source_count = (
            source_item.data(Qt.ItemDataRole.UserRole)
            if source_item is not None
            else 0
        ) or 0

        if name in UNIQUE_NAMES:
            category = "Unique Buffs"
        elif name in DEBUFF_NAMES:
            category = "Debuffs"
        else:
            category = "Buffs"

        source_text = source_item.text() if source_item is not None else ""
        searchable = f"{name} {source_text}".casefold()
        visible = (
            (effect_type == "All Effects" or effect_type == category)
            and (not self.missing_only.isChecked() or evidence != "available")
            and (not self.redundant_only.isChecked() or source_count > 1)
            and (not query or query in searchable)
        )
        self.table.setRowHidden(row, not visible)


def _refresh_with_group_catalog(self, *args, **kwargs):
    assert _ORIGINAL_REFRESH is not None
    result = _ORIGINAL_REFRESH(self, *args, **kwargs)
    _apply_reference_labels(self)
    _refresh_source_notes(self)
    return result


def _init_with_group_catalog(self, *args, **kwargs):
    assert _ORIGINAL_INIT is not None
    _ORIGINAL_INIT(self, *args, **kwargs)

    utility_index = self.effect_filter.findText("Utility")
    if utility_index >= 0:
        self.effect_filter.removeItem(utility_index)

    if self.effect_filter.findText("Unique Buffs") < 0:
        self.effect_filter.addItem("Unique Buffs")

    self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    self.table.currentCellChanged.connect(lambda *_: _refresh_source_notes(self))

    _coverage_notes_card(self)
    _apply_reference_labels(self)
    if self.table.rowCount() and self.table.currentRow() < 0:
        self.table.selectRow(0)
    _refresh_source_notes(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_INIT, _ORIGINAL_REFRESH, _ORIGINAL_SNAPSHOT_FOR_BUILDS
    if _INSTALLED:
        return

    from ui import coverage_page

    # Buffs & Debuffs is a raid-planning surface. Keep mechanic jobs and ad-hoc
    # utilities out; include group effects and support sets raid leads assign for
    # their unique effects. Magickasteal remains a Debuff.
    coverage_page.CORE_COVERAGE = COVERAGE_NAMES
    coverage_page.DEBUFFS = set(DEBUFF_NAMES)
    coverage_page.UTILITY = set()

    CoveragePage = coverage_page.CoveragePage
    _ORIGINAL_INIT = CoveragePage.__init__
    _ORIGINAL_REFRESH = CoveragePage.refresh
    _ORIGINAL_SNAPSHOT_FOR_BUILDS = CoveragePage.snapshot_for_builds

    CoveragePage._apply_coverage_filters = _apply_coverage_filters_with_unique
    CoveragePage.snapshot_for_builds = _snapshot_with_group_catalog
    CoveragePage.refresh = _refresh_with_group_catalog
    CoveragePage.__init__ = _init_with_group_catalog
    _INSTALLED = True
