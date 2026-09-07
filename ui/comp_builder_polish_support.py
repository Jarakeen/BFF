from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.components.foundry_card import FoundryCard
from ui.components.team_progress_panels import (
    BUILD_COVERAGE_ALIASES,
    DISPLAY_COVERAGE_EFFECTS,
    TeamCoverageGrid,
    TeamCoverageItem,
    coverage_from_declared_text,
)
from ui.ux_icons import icon_label


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_PICKER_REFRESH = None
_ORIGINAL_ASSIGNMENT_REFRESH = None
_ORIGINAL_ROLE_SYNC = None
_ORIGINAL_COVERAGE_SET_ITEMS = None


def _candidate_text(candidate) -> str:
    values = [
        getattr(candidate, "name", ""),
        getattr(candidate, "source_name", ""),
        getattr(candidate, "eso_class", ""),
        getattr(candidate, "role", ""),
        *(getattr(candidate, "gear_sets", ()) or ()),
        *(getattr(candidate, "skills", ()) or ()),
    ]
    return " ".join(str(value or "") for value in values).casefold()


def coverage_from_candidate_rows(rows: tuple[tuple[str, object], ...]) -> tuple[TeamCoverageItem, ...]:
    """Derive display coverage from the exact builds currently assigned in Comp Maker."""
    result: list[TeamCoverageItem] = []
    for effect in DISPLAY_COVERAGE_EFFECTS:
        aliases = BUILD_COVERAGE_ALIASES.get(effect, (effect.casefold(),))
        providers: list[str] = []
        for role_name, candidate in rows:
            text = _candidate_text(candidate)
            if not any(alias.casefold() in text for alias in aliases):
                continue
            provider = str(getattr(candidate, "name", "") or role_name or "Assigned build").strip()
            if provider and provider not in providers:
                providers.append(provider)
        result.append(
            TeamCoverageItem(
                name=effect,
                provider=", ".join(providers[:2]),
                covered=bool(providers),
            )
        )
    return tuple(result)


def merge_coverage(
    assigned: tuple[TeamCoverageItem, ...],
    declared: tuple[TeamCoverageItem, ...],
) -> tuple[TeamCoverageItem, ...]:
    """Prefer assigned-build evidence while preserving explicit provider declarations."""
    declared_by_name = {item.name: item for item in declared}
    merged: list[TeamCoverageItem] = []
    for item in assigned:
        other = declared_by_name.get(item.name)
        providers: list[str] = []
        for raw in (item.provider, other.provider if other is not None else ""):
            for provider in (piece.strip() for piece in raw.split(",")):
                if provider and provider not in providers:
                    providers.append(provider)
        merged.append(
            TeamCoverageItem(
                name=item.name,
                provider=", ".join(providers[:2]),
                covered=item.covered or bool(other and other.covered),
            )
        )
    return tuple(merged)


def _refresh_comp_progress_from_assignments(page) -> None:
    grid = getattr(page, "progress_coverage_grid", None)
    if grid is None:
        return

    from ui import team_progress_support

    declared = coverage_from_declared_text(team_progress_support._comp_declared_rows(page))
    applied = getattr(page, "_comp_applied_candidates", {}) or {}
    assigned = coverage_from_candidate_rows(tuple(applied.items()))
    grid.set_items(merge_coverage(assigned, declared))


def _set_coverage_items_with_icons(self, items: tuple[TeamCoverageItem, ...]) -> None:
    while self._layout.count():
        item = self._layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
    self._labels.clear()

    for index, item in enumerate(items):
        tile = QWidget()
        tile.setProperty("coverageTile", True)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        title = QLabel(item.name)
        title.setProperty("sidebarHeading", True)
        layout.addWidget(title)

        state_row = QWidget()
        state_layout = QHBoxLayout(state_row)
        state_layout.setContentsMargins(0, 0, 0, 0)
        state_layout.setSpacing(6)
        if item.covered:
            state_layout.addWidget(icon_label("circle-check", 15))
        else:
            missing = QLabel("○")
            missing.setFixedWidth(15)
            state_layout.addWidget(missing)

        state = QLabel(item.provider or "Not covered yet")
        state.setProperty("coverageCovered", item.covered)
        state_layout.addWidget(state, 1)
        layout.addWidget(state_row)

        self._layout.addWidget(tile, index // 5, index % 5)
        self._labels.append(state)


def _details_card(page) -> FoundryCard | None:
    wanted = {
        "Composition Details & Summary",
        "Selected Chair Setup & Evidence",
        "ESO Logs Catalog & Chair Evidence",
        "Build Catalog",
    }
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() in wanted:
            return card
    return None


def _polish_visible_controls(page) -> None:
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() == "Actions":
            card.set_icon("←")
            break

    details = _details_card(page)
    if details is not None:
        details.set_title("Build Catalog")

    combo = getattr(page, "comp_candidate_choice_combo", None)
    if combo is not None:
        combo.setMinimumHeight(38)
        combo.setProperty("compCandidateChoiceProminent", True)
        combo.setToolTip("Choose the build to assign to the selected role.")

    label = getattr(page, "comp_candidate_choice_label", None)
    if label is not None:
        label.setText("▼ BUILD OPTIONS • Choose the build to assign to the highlighted role")
        label.setProperty("compCandidateChoiceProminentLabel", True)


def _refresh_picker_with_role_language(page) -> None:
    assert _ORIGINAL_PICKER_REFRESH is not None
    _ORIGINAL_PICKER_REFRESH(page)
    label = getattr(page, "comp_candidate_choice_label", None)
    combo = getattr(page, "comp_candidate_choice_combo", None)
    if label is not None:
        if combo is not None and combo.count():
            label.setText("▼ BUILD OPTIONS • Choose the build to assign to the highlighted role")
        else:
            label.setText("▼ BUILD OPTIONS • No eligible build is available for this role")
    _refresh_comp_progress_from_assignments(page)


def _refresh_assignment_with_role_language(page) -> None:
    assert _ORIGINAL_ASSIGNMENT_REFRESH is not None
    _ORIGINAL_ASSIGNMENT_REFRESH(page)
    cue = getattr(page, "comp_assignment_cue_label", None)
    if cue is not None:
        cue.setText(
            cue.text()
            .replace("PLAYER / CHAIR", "ROLE")
            .replace("PLAYER/CHAIR", "ROLE")
            .replace("CHAIR", "ROLE")
            .replace("chair", "role")
        )


def _sync_role_language(page) -> None:
    assert _ORIGINAL_ROLE_SYNC is not None
    _ORIGINAL_ROLE_SYNC(page)
    title = getattr(page, "comp_chair_title_label", None)
    if title is not None:
        title.setText(title.text().replace("RAID CHAIR", "ROLE").replace("chair", "role"))


def _comp_init_with_polish(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _polish_visible_controls(self)
    _refresh_comp_progress_from_assignments(self)


def install() -> None:
    global _INSTALLED
    global _ORIGINAL_COMP_INIT, _ORIGINAL_PICKER_REFRESH
    global _ORIGINAL_ASSIGNMENT_REFRESH, _ORIGINAL_ROLE_SYNC, _ORIGINAL_COVERAGE_SET_ITEMS
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    from ui import comp_builder_assignment_cue_support as assignment_support
    from ui import comp_builder_candidate_picker_support as picker_support
    from ui import comp_builder_workspace_support as workspace_support
    from ui import team_progress_support

    _ORIGINAL_COVERAGE_SET_ITEMS = TeamCoverageGrid.set_items
    TeamCoverageGrid.set_items = _set_coverage_items_with_icons

    team_progress_support._refresh_comp_progress = _refresh_comp_progress_from_assignments

    _ORIGINAL_PICKER_REFRESH = picker_support._refresh_picker
    picker_support._refresh_picker = _refresh_picker_with_role_language

    _ORIGINAL_ASSIGNMENT_REFRESH = assignment_support._refresh_assignment_cue
    assignment_support._refresh_assignment_cue = _refresh_assignment_with_role_language

    _ORIGINAL_ROLE_SYNC = workspace_support._sync_selected_chair
    workspace_support._sync_selected_chair = _sync_role_language

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _comp_init_with_polish
    _INSTALLED = True
