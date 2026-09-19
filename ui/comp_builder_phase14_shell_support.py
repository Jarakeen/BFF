from __future__ import annotations

"""Owned Phase 14 presentation shell for Comp Builder.

The legacy matrix and candidate services remain authoritative underneath this
surface. The visible page follows the approved Work-chat layout:
Raid Brief -> Recommended Team Plan + Why This Plan -> Team Health.
"""

from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_RENDER_SLOTS = None
_ORIGINAL_REFRESH_CANDIDATES = None
_ORIGINAL_APPLY_ROSTER_CONTEXT = None

MAX_WIDGET_HEIGHT = 16_777_215

PRESENTATION_HEADERS = (
    "#",
    "PLAYER",
    "ROLE / CLASS",
    "RECOMMENDED BUILD (SETS)",
    "KEY RESPONSIBILITY",
    "STATUS",
)


def _card_any(page, *titles: str) -> FoundryCard | None:
    wanted = {title.strip() for title in titles}
    for card in page.findChildren(FoundryCard):
        if card.title_label.text().strip() in wanted:
            return card
    return None


def _workspace_root(page):
    item = page.workspace_layout.itemAt(0)
    workspace = item.widget() if item is not None else None
    return workspace.layout() if workspace is not None else None


def _detach_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        nested = item.layout()
        if nested is not None:
            _detach_layout(nested)


def _rehome(widget, layout) -> None:
    if widget is None:
        return
    parent = widget.parentWidget()
    old_layout = parent.layout() if parent is not None else None
    if old_layout is not None:
        old_layout.removeWidget(widget)
    widget.show()
    layout.addWidget(widget)


def _context_box(title: str, widget: QWidget) -> QWidget:
    host = QWidget()
    host.setProperty("compRaidBriefField", True)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    label = QLabel(title)
    label.setProperty("sidebarHeading", True)
    layout.addWidget(label)
    layout.addWidget(widget)
    return host


def _role_key(value: str) -> str:
    lowered = str(value or "").strip().casefold()
    if "tank" in lowered:
        return "tank"
    if "heal" in lowered:
        return "healer"
    if any(token in lowered for token in ("damage", "dps", "dd")):
        return "damage"
    return "other"


def _seat_key(value: object) -> str:
    text = " ".join(str(value or "").strip().casefold().replace("_", " ").replace("-", " ").split())
    return "-".join(text.split())


def _state_chair_for_row(page, row: int):
    state = getattr(page, "_comp_plan_state", None)
    if state is None or row < 0:
        return None
    slot = page._cell_text(row, 0) or f"Slot {row + 1}"
    wanted = _seat_key(slot)
    return next(
        (
            chair
            for chair in tuple(getattr(state, "chairs", ()) or ())
            if _seat_key(getattr(chair, "seat_id", "")) == wanted
        ),
        None,
    )


def _candidate_for_row(page, row: int):
    if row < 0:
        return None
    slot = page._cell_text(row, 0) or f"Slot {row + 1}"
    applied = getattr(page, "_comp_applied_candidates", {}).get(slot)
    if applied is not None:
        return applied
    try:
        from ui import comp_builder_build_candidate_support as candidate_support

        candidates = candidate_support._chair_candidates(page, row)
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    return candidates[0] if candidates else None


def _candidate_sets(candidate) -> tuple[str, str]:
    if candidate is None:
        return ("Open", "")
    gear = tuple(
        str(value).strip()
        for value in (getattr(candidate, "five_piece_sets", ()) or ())
        if str(value).strip()
    )
    if len(gear) >= 2:
        return (gear[0], gear[1])
    if len(gear) == 1:
        return (gear[0], "")
    return ("No five-piece sets resolved", "")


def _candidate_label(candidate) -> str:
    first, second = _candidate_sets(candidate)
    return " + ".join(value for value in (first, second) if value)


def _manual_sets_for_slot(page, slot_name: str) -> tuple[str, ...]:
    return tuple(
        str(value).strip()
        for value in getattr(page, "_comp_manual_gear_sets_by_slot", {}).get(slot_name, ())
        if str(value).strip()
    )


def _catalog_set_names(page) -> tuple[str, ...]:
    cached = getattr(page, "_comp_gear_catalog_names", None)
    if cached is not None:
        return tuple(cached)

    try:
        from engine.config import DEFAULT_DATABASE
        from minmax.gear_set_repository import GearSetRepository

        names = tuple(
            dict.fromkeys(
                str(row.name or "").strip()
                for row in GearSetRepository(DEFAULT_DATABASE).list_sets()
                if str(row.name or "").strip()
            )
        )
    except Exception:
        names = ()
    page._comp_gear_catalog_names = names
    return names


def _canonical_catalog_set_name(page, value: object) -> str:
    wanted = str(value or "").strip()
    if not wanted:
        return ""
    return next(
        (
            name
            for name in _catalog_set_names(page)
            if name.casefold() == wanted.casefold()
        ),
        "",
    )


def _add_planned_gear_set(page, set_name: str) -> None:
    row = _selected_backend_row(page)
    if row < 0:
        return
    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    chair_state = _state_chair_for_row(page, row)
    if chair_state is not None and chair_state.is_locked("gear"):
        page.status.warning(f"{slot_name} gear is locked in this Raid Plan.")
        return

    canonical = _canonical_catalog_set_name(page, set_name)
    if not canonical:
        page.status.warning("Choose a set from the Gear Catalog before adding it.")
        return

    if chair_state is not None:
        existing = tuple(chair_state.planned_gear_sets or ())
        if any(value.casefold() == canonical.casefold() for value in existing):
            page.status.info(f"{canonical} is already planned for {slot_name}.")
            return
        page._comp_plan_state = page._comp_plan_state.with_chair(
            chair_state.with_changes(planned_gear_sets=(*existing, canonical))
        )
    else:
        store = getattr(page, "_comp_manual_gear_sets_by_slot", None)
        if store is None:
            page._comp_manual_gear_sets_by_slot = {}
            store = page._comp_manual_gear_sets_by_slot
        existing = list(_manual_sets_for_slot(page, slot_name))
        if any(value.casefold() == canonical.casefold() for value in existing):
            return
        existing.append(canonical)
        store[slot_name] = tuple(existing)

    page.status.success(f"Added {canonical} to {slot_name}.")
    _refresh_shell(page)


def _remove_planned_gear_set(page, set_name: str) -> None:
    row = _selected_backend_row(page)
    if row < 0:
        return
    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    chair_state = _state_chair_for_row(page, row)
    if chair_state is not None and chair_state.is_locked("gear"):
        page.status.warning(f"{slot_name} gear is locked in this Raid Plan.")
        return

    wanted = str(set_name or "").strip().casefold()
    if chair_state is not None:
        remaining = tuple(
            value
            for value in tuple(chair_state.planned_gear_sets or ())
            if value.casefold() != wanted
        )
        page._comp_plan_state = page._comp_plan_state.with_chair(
            chair_state.with_changes(planned_gear_sets=remaining)
        )
    else:
        store = getattr(page, "_comp_manual_gear_sets_by_slot", None)
        if store is not None:
            remaining = tuple(
                value
                for value in _manual_sets_for_slot(page, slot_name)
                if value.casefold() != wanted
            )
            if remaining:
                store[slot_name] = remaining
            else:
                store.pop(slot_name, None)

    page.status.success(f"Removed {set_name} from {slot_name}.")
    _refresh_shell(page)


def _toggle_manual_set(page, set_name: str) -> None:
    row = _selected_backend_row(page)
    if row < 0:
        return
    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    chair_state = _state_chair_for_row(page, row)
    if chair_state is not None and chair_state.is_locked("gear"):
        page.status.warning(f"{slot_name} gear is locked in this Raid Plan.")
        return

    name = str(set_name or "").strip()
    if not name:
        return

    store = getattr(page, "_comp_manual_gear_sets_by_slot", None)
    if store is None:
        page._comp_manual_gear_sets_by_slot = {}
        store = page._comp_manual_gear_sets_by_slot

    current = list(_manual_sets_for_slot(page, slot_name))
    matching = next(
        (value for value in current if value.casefold() == name.casefold()),
        None,
    )
    if matching is not None:
        current.remove(matching)
    else:
        if len(current) >= 2:
            page.status.warning(
                f"{slot_name} already has two manually selected five-piece sets. "
                "Remove one before choosing another."
            )
            return
        current.append(name)

    if current:
        store[slot_name] = tuple(current)
    else:
        store.pop(slot_name, None)

    if chair_state is not None:
        from engine.config import get_data_dir
        from services.comp_builder_build_candidates import _five_piece_set_names

        existing = tuple(chair_state.planned_gear_sets or ())
        existing_five = {
            value.casefold()
            for value in _five_piece_set_names(get_data_dir() / "eso.db", existing)
        }
        preserved_non_five = tuple(
            value for value in existing if value.casefold() not in existing_five
        )
        planned = tuple((*preserved_non_five, *current))
        page._comp_plan_state = page._comp_plan_state.with_chair(
            chair_state.with_changes(planned_gear_sets=planned)
        )

    package = " + ".join(current) if current else "automatic recommendation"
    page.status.success(f"{slot_name} gear package: {package}.")
    _refresh_shell(page)


def _refresh_manual_set_picker(page, candidates) -> None:
    host = getattr(page, "comp_phase14_set_picker_host", None)
    layout = getattr(page, "comp_phase14_set_picker_layout", None)
    if host is None or layout is None:
        return

    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()

    row = _selected_backend_row(page)
    if row < 0:
        host.setVisible(False)
        return

    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    chair_state = _state_chair_for_row(page, row)
    planned_sets = (
        tuple(chair_state.planned_gear_sets or ())
        if chair_state is not None
        else _manual_sets_for_slot(page, slot_name)
    )

    heading = QLabel("ASSIGN GEAR")
    heading.setProperty("sidebarHeading", True)
    layout.addWidget(heading)

    help_text = QLabel(
        "Search the full Gear Catalog and assign sets directly. "
        "Recommendations below are suggestions, not restrictions."
    )
    help_text.setWordWrap(True)
    help_text.setProperty("compManualSetSummary", True)
    layout.addWidget(help_text)

    if planned_sets:
        current_label = QLabel("CURRENT PLAN")
        current_label.setProperty("sidebarHeading", True)
        layout.addWidget(current_label)
        for name in planned_sets:
            row_host = QWidget()
            row_layout = QHBoxLayout(row_host)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            label = QLabel(name)
            label.setWordWrap(True)
            row_layout.addWidget(label, 1)
            remove = QPushButton("Remove")
            remove.setProperty("compManualSetChoice", True)
            remove.setEnabled(
                not (
                    chair_state is not None
                    and chair_state.is_locked("gear")
                )
            )
            remove.clicked.connect(
                lambda _checked=False, set_name=name: _remove_planned_gear_set(
                    page, set_name
                )
            )
            row_layout.addWidget(remove)
            layout.addWidget(row_host)
    else:
        empty = QLabel("Current plan: no gear assigned yet.")
        empty.setProperty("compManualSetSummary", True)
        layout.addWidget(empty)

    search_row = QWidget()
    search_layout = QHBoxLayout(search_row)
    search_layout.setContentsMargins(0, 0, 0, 0)
    search_layout.setSpacing(6)

    picker = QComboBox()
    picker.setEditable(True)
    picker.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    picker.addItems(list(_catalog_set_names(page)))
    picker.setCurrentIndex(-1)
    picker.setPlaceholderText("Search all gear sets…")
    picker.setProperty("compDirectGearPicker", True)
    if picker.completer() is not None:
        picker.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        picker.completer().setFilterMode(Qt.MatchFlag.MatchContains)
    picker.setEnabled(
        not (
            chair_state is not None
            and chair_state.is_locked("gear")
        )
    )
    search_layout.addWidget(picker, 1)

    add = QPushButton("Add Set")
    add.setProperty("compManualSetChoice", True)
    add.setEnabled(picker.isEnabled())
    add.clicked.connect(
        lambda *_: _add_planned_gear_set(page, picker.currentText())
    )
    search_layout.addWidget(add)
    layout.addWidget(search_row)

    suggestions: list[str] = []
    seen = {value.casefold() for value in planned_sets}
    for candidate in candidates:
        for name in getattr(candidate, "gear_sets", ()) or ():
            text = str(name or "").strip()
            key = text.casefold()
            if text and key not in seen:
                seen.add(key)
                suggestions.append(text)

    if suggestions:
        suggested_label = QLabel("SUGGESTED BY COMP MAKER")
        suggested_label.setProperty("sidebarHeading", True)
        layout.addWidget(suggested_label)
        for name in suggestions[:8]:
            button = QPushButton(f"+ {name}")
            button.setProperty("compManualSetChoice", True)
            button.setEnabled(picker.isEnabled())
            button.setToolTip(
                "Add this recommendation to the current chair. "
                "You can also search any Gear Catalog set above."
            )
            button.clicked.connect(
                lambda _checked=False, set_name=name: _add_planned_gear_set(
                    page, set_name
                )
            )
            layout.addWidget(button)

    host.setVisible(True)

def _responsibility_for_row(page, row: int) -> str:
    for column in (4, 6, 7):
        value = page._cell_text(row, column)
        if value:
            pieces = page._split_values(value)
            if pieces:
                return pieces[0]
            return value
    return "Open responsibility"


def _status_for_row(page, row: int, candidate) -> str:
    player = page._cell_text(row, 11).strip()
    slot = page._cell_text(row, 0) or f"Slot {row + 1}"
    chair_state = _state_chair_for_row(page, row)
    state_sets = tuple(chair_state.planned_gear_sets or ()) if chair_state is not None else ()
    manual_sets = _manual_sets_for_slot(page, slot)
    applied_candidate = getattr(page, "_comp_applied_candidates", {}).get(slot)
    applied = applied_candidate is not None
    applied_sets = tuple(
        str(value).strip()
        for value in (
            getattr(applied_candidate, "five_piece_sets", ())
            or getattr(applied_candidate, "gear_sets", ())
            or ()
        )
        if str(value).strip()
    )
    planned_gear = bool(state_sets or manual_sets or applied_sets)

    if not player or player.casefold().startswith("recruit"):
        return "Planned gear" if planned_gear else "Needs gear"
    if candidate is None and not planned_gear:
        return "Needs build"
    if applied and bool(getattr(candidate, "complete_build", False)):
        return "Ready"
    if applied or manual_sets:
        return "1 change"
    return "Review"


def _group_rows(page) -> dict[str, list[int]]:
    groups = {"tank": [], "healer": [], "damage": [], "other": []}
    for row in range(page.matrix_table.rowCount()):
        groups[_role_key(page._cell_text(row, 1))].append(row)
    return groups


def _refresh_plan_table(page) -> None:
    table = getattr(page, "comp_phase14_plan_table", None)
    if table is None:
        return

    # Raid Plan seat classes are authoritative for a Raid Plan-bound Comp session.
    # Reapply before rendering so later candidate/source refreshes cannot erase them.
    raid_classes = dict(getattr(page, "_raid_plan_class_by_seat", {}) or {})
    if raid_classes:
        from ui.comp_builder_roster_intake_support import apply_raid_plan_class_constraints
        apply_raid_plan_class_constraints(page, raid_classes)

    groups = _group_rows(page)
    ordered = (
        ("tank", "TANKS"),
        ("healer", "HEALERS"),
        ("damage", "DAMAGE"),
        ("other", "OTHER"),
    )
    visible_rows = sum(len(rows) + (1 if rows else 0) for _key, _label in ordered for rows in (groups[_key],))

    prior_backend = getattr(page, "_comp_phase14_selected_backend_row", 0)
    page._comp_phase14_display_to_backend = {}
    table.blockSignals(True)
    table.clearContents()
    table.setRowCount(visible_rows)

    display_row = 0
    selected_display = -1
    for key, label in ordered:
        source_rows = groups[key]
        if not source_rows:
            continue

        group_item = QTableWidgetItem(f"{label}  ({len(source_rows)})")
        font = QFont(group_item.font())
        font.setBold(True)
        group_item.setFont(font)
        group_item.setFlags(Qt.ItemFlag.NoItemFlags)
        table.setItem(display_row, 0, group_item)
        table.setSpan(display_row, 0, 1, len(PRESENTATION_HEADERS))
        display_row += 1

        for backend_row in source_rows:
            page._comp_phase14_display_to_backend[display_row] = backend_row
            if backend_row == prior_backend:
                selected_display = display_row

            candidate = _candidate_for_row(page, backend_row)
            chair_state = _state_chair_for_row(page, backend_row)
            player = (
                str(getattr(chair_state, "player_name", "") or "").strip()
                if chair_state is not None
                else page._cell_text(backend_row, 11)
            ) or "Recruit"
            role = (
                str(getattr(chair_state, "role", "") or "").strip()
                if chair_state is not None
                else page._cell_text(backend_row, 1)
            ) or "Unresolved"
            selected_class = (
                str(getattr(chair_state, "eso_class", "") or "").strip()
                if chair_state is not None
                else page._selected_class(backend_row)
            ) or "Any class"
            role_class = role if selected_class == "Any class" else f"{role} • {selected_class}"
            slot_name = page._cell_text(backend_row, 0) or f"Slot {backend_row + 1}"
            state_sets = tuple(
                str(value).strip()
                for value in (getattr(chair_state, "planned_gear_sets", ()) or ())
                if str(value).strip()
            ) if chair_state is not None else ()
            manual_sets = _manual_sets_for_slot(page, slot_name)
            build_label = (
                " + ".join(state_sets)
                if state_sets
                else " + ".join(manual_sets)
                if manual_sets
                else _candidate_label(candidate)
            )
            state_responsibility = ""
            if chair_state is not None:
                state_responsibility = (
                    str(getattr(chair_state, "primary_assignment", "") or "").strip()
                    or next(
                        (
                            str(value).strip()
                            for value in (getattr(chair_state, "utility_assignments", ()) or ())
                            if str(value).strip()
                        ),
                        "",
                    )
                )
            values = (
                str(backend_row + 1),
                player,
                role_class,
                build_label,
                state_responsibility or _responsibility_for_row(page, backend_row),
                _status_for_row(page, backend_row, candidate),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if column == 5:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(display_row, column, item)
            display_row += 1

    table.blockSignals(False)
    if selected_display < 0:
        selected_display = next(iter(page._comp_phase14_display_to_backend), -1)
    if selected_display >= 0:
        table.selectRow(selected_display)


def _selected_backend_row(page) -> int:
    table = getattr(page, "comp_phase14_plan_table", None)
    if table is None:
        return 0 if page.matrix_table.rowCount() else -1
    row = table.currentRow()
    backend = getattr(page, "_comp_phase14_display_to_backend", {}).get(row)
    if backend is not None:
        return backend
    return getattr(page, "_comp_phase14_selected_backend_row", 0)


def _select_plan_row(page, display_row: int, _column: int = 0) -> None:
    backend = getattr(page, "_comp_phase14_display_to_backend", {}).get(display_row)
    if backend is None:
        return
    page._comp_phase14_selected_backend_row = backend
    page.matrix_table.selectRow(backend)
    _refresh_why(page)


def _candidate_source(candidate) -> str:
    return {
        "saved_build": "Saved build",
        "esologs_snapshot": "ESO Logs evidence",
        "reference_template": "Reference template",
    }.get(str(getattr(candidate, "source_kind", "") or ""), "Build evidence")


def _alternative_text(candidate) -> str:
    if candidate is None:
        return "No alternate recommendation resolved."
    name = _candidate_label(candidate)
    reasons = tuple(getattr(candidate, "score_reasons", ()) or ())
    return name if not reasons else f"{name}\n{reasons[0]}"


def _confidence_level(candidate) -> tuple[str, str, str, str]:
    if candidate is None:
        return ("review", "Needs review", "#243E4A", "#59AEB3")

    score = float(getattr(candidate, "score", 0.0) or 0.0)
    unresolved = tuple(getattr(candidate, "unresolved", ()) or ())
    complete = bool(getattr(candidate, "complete_build", False))

    if unresolved and not complete:
        return ("review", "Needs review", "#243E4A", "#59AEB3")
    if score >= 80.0:
        return ("high", "High confidence", "#183F35", "#2F8C74")
    if score >= 60.0:
        return ("medium", "Medium confidence", "#4A3B1B", "#C8A46A")
    return ("low", "Low confidence", "#472828", "#B86A6A")


def _style_confidence_badge(label: QLabel, candidate) -> None:
    level, title, background, border = _confidence_level(candidate)
    score = float(getattr(candidate, "score", 0.0) or 0.0) if candidate is not None else 0.0
    source = _candidate_source(candidate) if candidate is not None else "No evidence"
    label.setProperty("confidenceLevel", level)
    label.setText(
        f"{title} • {source} • relevance {score:.1f}"
        if candidate is not None
        else title
    )
    label.setStyleSheet(
        "QLabel {"
        f"background: {background};"
        f"border: 1px solid {border};"
        "border-radius: 7px;"
        "padding: 5px 10px;"
        "font-weight: 600;"
        "}"
    )


def _set_choice_state(frame: QFrame, *, selected: bool, enabled: bool) -> None:
    frame.setEnabled(enabled)
    frame.setProperty("choiceSelected", selected)
    frame.setCursor(
        Qt.CursorShape.PointingHandCursor
        if enabled
        else Qt.CursorShape.ArrowCursor
    )
    border = "#C8A46A" if selected else "#50666A"
    width = "2px" if selected else "1px"
    background = "#13262B" if selected else "#0F1B1F"
    frame.setStyleSheet(
        "QFrame[compCandidateChoice=\"true\"] {"
        f"border: {width} solid {border};"
        "border-radius: 7px;"
        f"background: {background};"
        "}"
        "QFrame[compCandidateChoice=\"true\"]:hover {"
        "border: 2px solid #C8A46A;"
        "background: #13262B;"
        "}"
    )


def _apply_choice(page, frame: QFrame) -> None:
    candidate = getattr(frame, "_comp_candidate", None)
    row = _selected_backend_row(page)
    if candidate is None or row < 0:
        return

    from ui import comp_builder_build_candidate_support as candidate_support

    slot_name = candidate_support._set_candidate_for_row(page, row, candidate)
    page.status.success(
        f"Applied {_candidate_label(candidate)} to {slot_name}. "
        "The plan now uses this gear recommendation."
    )
    _refresh_shell(page)


def _refresh_why(page) -> None:
    if not hasattr(page, "comp_phase14_recommendation"):
        return

    row = _selected_backend_row(page)
    if row < 0 or row >= page.matrix_table.rowCount():
        page.comp_phase14_why_header.setText("No player selected")
        page.comp_phase14_recommendation.setText("No recommendation available.")
        page.comp_phase14_set_one.setText("No recommendation")
        page.comp_phase14_set_two.setText("")
        page.comp_phase14_set_plus.setVisible(False)
        page.comp_phase14_confidence.setText("No evidence")
        page.comp_phase14_role_footer.setText("No role selected")
        page.comp_phase14_why_text.setText("Select a player in Recommended Team Plan.")
        page.comp_phase14_alt_one.setText("—")
        page.comp_phase14_alt_two.setText("—")
        for frame in (
            page.comp_phase14_recommendation_frame,
            page.comp_phase14_alt_one_frame,
            page.comp_phase14_alt_two_frame,
        ):
            frame._comp_candidate = None
            _set_choice_state(frame, selected=False, enabled=False)
        _style_confidence_badge(page.comp_phase14_confidence, None)
        _refresh_manual_set_picker(page, ())
        refresh_sources = getattr(page, "comp_phase14_refresh_sources", None)
        if refresh_sources is not None:
            refresh_sources.setVisible(False)
        return

    player = page._cell_text(row, 11) or "Recruit"
    slot = page._cell_text(row, 0) or f"Slot {row + 1}"
    role = page._cell_text(row, 1) or "Unresolved"
    selected_class = page._selected_class(row) or "Any class"
    page.comp_phase14_why_header.setText(
        f"{player}  •  {slot}  •  {selected_class}"
    )

    try:
        from ui import comp_builder_build_candidate_support as candidate_support

        candidates = tuple(candidate_support._chair_candidates(page, row))
    except (AttributeError, OSError, TypeError, ValueError):
        candidates = ()

    slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
    applied = getattr(page, "_comp_applied_candidates", {}).get(slot_name)
    preferred = candidates[0] if candidates else applied
    if preferred is None:
        page.comp_phase14_recommendation.setText(
            "No eligible build recommendation resolved."
        )
        page.comp_phase14_set_one.setText("No eligible build")
        page.comp_phase14_set_two.setText("")
        page.comp_phase14_set_plus.setVisible(False)
        page.comp_phase14_confidence.setText("Needs review")
        page.comp_phase14_role_footer.setText(f"{selected_class}  •  {role}")
        page.comp_phase14_why_text.setText(
            f"No source-backed recommendation is currently available for {role}. "
            "The slot remains intentionally unresolved."
        )
        page.comp_phase14_alt_one.setText(
            "No alternate recommendation resolved."
        )
        page.comp_phase14_alt_two.setText(
            "No alternate recommendation resolved."
        )
        for frame in (
            page.comp_phase14_recommendation_frame,
            page.comp_phase14_alt_one_frame,
            page.comp_phase14_alt_two_frame,
        ):
            frame._comp_candidate = None
            _set_choice_state(frame, selected=False, enabled=False)
        _style_confidence_badge(page.comp_phase14_confidence, None)
        _refresh_manual_set_picker(page, ())
        refresh_sources = getattr(page, "comp_phase14_refresh_sources", None)
        if refresh_sources is not None:
            refresh_sources.setVisible(True)
            refresh_sources.setText("Load Current Ranked Builds")
        return

    refresh_sources = getattr(page, "comp_phase14_refresh_sources", None)
    if refresh_sources is not None:
        refresh_sources.setVisible(False)

    page.comp_phase14_recommendation.setText(_candidate_label(preferred))
    set_one, set_two = _candidate_sets(preferred)
    page.comp_phase14_set_one.setText(set_one)
    page.comp_phase14_set_two.setText(
        set_two if set_two else "No second set resolved"
    )
    page.comp_phase14_set_plus.setVisible(bool(set_two))

    _style_confidence_badge(page.comp_phase14_confidence, preferred)
    page.comp_phase14_role_footer.setText(f"{selected_class}  •  {role}")

    reasons = tuple(getattr(preferred, "score_reasons", ()) or ())
    obligations = []
    for column in (4, 6, 7):
        obligations.extend(page._split_values(page._cell_text(row, column)))
    why_parts = list(reasons[:3])
    if obligations:
        why_parts.append("Plan obligation: " + " • ".join(obligations[:2]))
    if not why_parts:
        why_parts.append(
            "This is the highest-ranked eligible evidence for the selected "
            "player, role, class, and trial."
        )
    page.comp_phase14_why_text.setText(" ".join(why_parts))

    _refresh_manual_set_picker(page, candidates)

    alternatives = [
        item
        for item in candidates
        if item.candidate_id != preferred.candidate_id
    ]
    alt_one = alternatives[0] if alternatives else None
    alt_two = alternatives[1] if len(alternatives) > 1 else None
    page.comp_phase14_alt_one.setText(_alternative_text(alt_one))
    page.comp_phase14_alt_two.setText(_alternative_text(alt_two))

    page.comp_phase14_recommendation_frame._comp_candidate = preferred
    page.comp_phase14_alt_one_frame._comp_candidate = alt_one
    page.comp_phase14_alt_two_frame._comp_candidate = alt_two

    selected_id = (
        str(getattr(applied, "candidate_id", "") or "")
        if applied is not None
        else str(getattr(preferred, "candidate_id", "") or "")
    )
    _set_choice_state(
        page.comp_phase14_recommendation_frame,
        selected=preferred.candidate_id == selected_id,
        enabled=True,
    )
    _set_choice_state(
        page.comp_phase14_alt_one_frame,
        selected=bool(alt_one and alt_one.candidate_id == selected_id),
        enabled=alt_one is not None,
    )
    _set_choice_state(
        page.comp_phase14_alt_two_frame,
        selected=bool(alt_two and alt_two.candidate_id == selected_id),
        enabled=alt_two is not None,
    )

def _health_tile(
    title: str,
    symbol: str,
    state: str,
) -> tuple[QWidget, QLabel, QLabel]:
    tile = QFrame()
    tile.setProperty("compHealthTile", True)
    tile.setProperty("healthState", state)

    row = QHBoxLayout(tile)
    row.setContentsMargins(10, 7, 10, 7)
    row.setSpacing(10)

    indicator = QLabel(symbol)
    indicator.setObjectName(f"compHealthIndicator_{state}")
    indicator.setProperty("compHealthIndicator", True)
    indicator.setProperty("healthState", state)
    indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
    indicator.setFixedSize(34, 34)

    palette = {
        "covered": ("#2ECC71", "#082A18"),
        "missing": ("#FF625E", "#351010"),
        "duplicate": ("#F0B84B", "#33240A"),
        "recruit": ("#59B6E8", "#0A2433"),
    }
    foreground, background = palette[state]
    indicator.setStyleSheet(
        "QLabel {"
        f"color: {foreground};"
        f"background: {background};"
        f"border: 2px solid {foreground};"
        "border-radius: 17px;"
        "font-weight: 700;"
        "font-size: 18px;"
        "}"
    )

    text_host = QWidget()
    text_layout = QVBoxLayout(text_host)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(1)

    heading = QLabel(title)
    heading.setProperty("sidebarHeading", True)
    value = QLabel("—")
    detail = QLabel("")
    value.setWordWrap(True)
    detail.setWordWrap(True)

    text_layout.addWidget(heading)
    text_layout.addWidget(value)
    text_layout.addWidget(detail)

    row.addWidget(indicator, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(text_host, 1)
    return tile, value, detail


def _effective_sets_for_row(page, row: int) -> tuple[str, ...]:
    """Return the exact gear package represented by the current visible plan row."""
    slot = page._cell_text(row, 0) or f"Slot {row + 1}"
    manual = _manual_sets_for_slot(page, slot)
    if manual:
        return manual

    applied = (getattr(page, "_comp_applied_candidates", {}) or {}).get(slot)
    if applied is None:
        return ()
    return tuple(
        str(value).strip()
        for value in (
            getattr(applied, "five_piece_sets", ())
            or getattr(applied, "gear_sets", ())
            or ()
        )
        if str(value).strip()
    )


def _effective_coverage_rows(page) -> tuple[tuple[str, object], ...]:
    """Project current chair state for Team Health, including manual gear overrides."""
    from types import SimpleNamespace

    rows: list[tuple[str, object]] = []
    applied = getattr(page, "_comp_applied_candidates", {}) or {}
    for row in range(page.matrix_table.rowCount()):
        slot = page._cell_text(row, 0) or f"Slot {row + 1}"
        manual = _manual_sets_for_slot(page, slot)
        candidate = applied.get(slot)
        if manual:
            candidate = SimpleNamespace(
                name=slot,
                source_name="Manual Comp plan",
                eso_class=page._selected_class(row),
                role=page._cell_text(row, 1),
                gear_sets=manual,
                five_piece_sets=manual,
                skills=tuple(getattr(candidate, "skills", ()) or ()) if candidate is not None else (),
            )
        if candidate is not None:
            rows.append((slot, candidate))
    return tuple(rows)


def _refresh_health(page) -> None:
    if not hasattr(page, "comp_phase14_health_covered"):
        return

    state = getattr(page, "_comp_plan_state", None)
    if state is not None:
        try:
            from engine.config import DEFAULT_DATABASE
            from services.comp_plan_health_service import CompPlanHealthService

            health = CompPlanHealthService(DEFAULT_DATABASE).evaluate(state)
        except (AttributeError, ImportError, OSError, TypeError, ValueError):
            health = None

        if health is not None:
            total = len(health.required_effects)
            supported = health.planned_or_static_required_count
            page.comp_phase14_health_covered.setText(
                f"Planned {supported} / {total}"
                if total
                else "Coverage unresolved"
            )
            page.comp_phase14_health_covered_detail.setText(
                (
                    f"{len(health.covered_required)} static • "
                    f"{len(health.conditional_required)} planned/conditional"
                )
                if total
                else "No required effect profile"
            )

            assigned_unproven = [
                review
                for review in health.assignment_reviews
                if review.effect_name in health.required_effects
                and review.state == "assigned_unproven"
            ]
            if assigned_unproven:
                review = assigned_unproven[0]
                page.comp_phase14_health_missing.setText(review.effect_name)
                page.comp_phase14_health_missing_detail.setText(
                    "Assigned to "
                    + ", ".join(review.primary_seats)
                    + " • source not proven"
                )
            else:
                first_missing = (
                    health.missing_required[0]
                    if health.missing_required
                    else "None"
                )
                page.comp_phase14_health_missing.setText(first_missing)
                page.comp_phase14_health_missing_detail.setText(
                    "No reviewed source in current Comp plan"
                    if health.missing_required
                    else "No tracked required gaps"
                )

            duplicate_assignments = [
                review
                for review in health.assignment_reviews
                if review.duplicate_primary
            ]
            if duplicate_assignments:
                review = duplicate_assignments[0]
                page.comp_phase14_health_duplicate.setText(review.effect_name)
                page.comp_phase14_health_duplicate_detail.setText(
                    "Multiple primary assignments: "
                    + ", ".join(review.primary_seats)
                )
            else:
                first_duplicate = (
                    health.duplicate_effects[0]
                    if health.duplicate_effects
                    else "None"
                )
                page.comp_phase14_health_duplicate.setText(first_duplicate)
                page.comp_phase14_health_duplicate_detail.setText(
                    "Multiple planned sources for the same effect"
                    if health.duplicate_effects
                    else "No duplicated tracked effect"
                )

            if health.open_gear_seats:
                count = len(health.open_gear_seats)
                page.comp_phase14_health_recruit.setText(
                    f"{count} gear gap" if count == 1 else f"{count} gear gaps"
                )
                page.comp_phase14_health_recruit_detail.setText(
                    f"{len(health.open_player_seats)} open player seat(s) • "
                    f"{len(health.open_player_seats) - count} already have planned gear"
                )
            elif health.open_player_seats:
                page.comp_phase14_health_recruit.setText(
                    f"{len(health.open_player_seats)} open player seat(s)"
                )
                page.comp_phase14_health_recruit_detail.setText(
                    "All open seats already have planned gear / setup"
                )
            else:
                page.comp_phase14_health_recruit.setText("None")
                page.comp_phase14_health_recruit_detail.setText("All player slots filled")
            return

    # Compatibility fallback for ad-hoc/unbound Comp sessions. This path is not
    # authoritative for Raid Plan-bound work and will be retired with legacy state.
    try:
        from ui import comp_builder_polish_support as polish
        from ui import team_progress_support
        from ui.components.team_progress_panels import coverage_from_declared_text

        declared = coverage_from_declared_text(team_progress_support._comp_declared_rows(page))
        assigned = polish.coverage_from_candidate_rows(_effective_coverage_rows(page))
        merged = polish.merge_coverage(assigned, declared)
    except (AttributeError, ImportError, TypeError, ValueError):
        merged = ()

    covered = [item for item in merged if item.covered]
    missing = [item for item in merged if not item.covered]
    total = len(merged)
    page.comp_phase14_health_covered.setText(
        f"Covered {len(covered)} / {total}" if total else "Coverage unresolved"
    )
    page.comp_phase14_health_covered_detail.setText("Legacy ad-hoc coverage projection")

    first_missing = missing[0].name if missing else "None"
    page.comp_phase14_health_missing.setText(first_missing)
    page.comp_phase14_health_missing_detail.setText(
        "No source in current plan" if missing else "No tracked gaps"
    )

    set_counts: Counter[str] = Counter()
    for row in range(page.matrix_table.rowCount()):
        for gear in _effective_sets_for_row(page, row):
            if gear:
                set_counts[str(gear)] += 1
    duplicates = [name for name, count in set_counts.items() if count > 1]
    page.comp_phase14_health_duplicate.setText(duplicates[0] if duplicates else "None")
    page.comp_phase14_health_duplicate_detail.setText(
        "Legacy duplicate set projection" if duplicates else "No duplicated tracked set"
    )

    recruits: list[tuple[str, str, bool]] = []
    for row in range(page.matrix_table.rowCount()):
        player = page._cell_text(row, 11).strip()
        if not player or player.casefold().startswith("recruit"):
            role = page._cell_text(row, 1) or "Open role"
            selected_class = page._selected_class(row)
            need = role if selected_class == "Any class" else f"{selected_class} {role}"
            has_gear = bool(_effective_sets_for_row(page, row))
            recruits.append((player or "Recruit", need, has_gear))

    unresolved_gear = [row for row in recruits if not row[2]]
    if unresolved_gear:
        page.comp_phase14_health_recruit.setText(
            f"{len(unresolved_gear)} gear gap"
            if len(unresolved_gear) == 1
            else f"{len(unresolved_gear)} gear gaps"
        )
        page.comp_phase14_health_recruit_detail.setText(
            f"{len(recruits)} open player seat(s) • "
            f"{len(recruits) - len(unresolved_gear)} already have planned gear"
        )
    elif recruits:
        page.comp_phase14_health_recruit.setText(f"{len(recruits)} open player seat(s)")
        page.comp_phase14_health_recruit_detail.setText(
            "All open seats already have planned gear / setup"
        )
    else:
        page.comp_phase14_health_recruit.setText("None")
        page.comp_phase14_health_recruit_detail.setText("All player slots filled")

def _refresh_shell(page) -> None:
    if not hasattr(page, "comp_phase14_plan_table"):
        return
    _refresh_plan_table(page)
    _refresh_why(page)
    _refresh_health(page)


def _apply_plan_geometry(page, size: int) -> None:
    """Keep 4-player plans compact while allowing full 12-player plans to grow.

    The page-level scroll area remains the fallback for short windows, while the
    table keeps its own vertical scrollbar for roster rows that still exceed the
    available middle-panel height.
    """
    plan_card = getattr(page, "comp_phase14_plan_card", None)
    why_card = getattr(page, "comp_phase14_why_card", None)
    plan_table = getattr(page, "comp_phase14_plan_table", None)

    if size == 4:
        card_minimum = 520
        card_maximum = 640
        table_minimum = 360
        table_maximum = 600
        card_policy = QSizePolicy.Policy.Preferred
        table_policy = QSizePolicy.Policy.Preferred
    else:
        card_minimum = 620
        card_maximum = MAX_WIDGET_HEIGHT
        table_minimum = 540
        table_maximum = MAX_WIDGET_HEIGHT
        card_policy = QSizePolicy.Policy.Expanding
        table_policy = QSizePolicy.Policy.Expanding

    for card in (plan_card, why_card):
        if card is None:
            continue
        card.setMinimumHeight(card_minimum)
        card.setMaximumHeight(card_maximum)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, card_policy)

    if plan_table is not None:
        plan_table.setMinimumHeight(table_minimum)
        plan_table.setMaximumHeight(table_maximum)
        plan_table.setSizePolicy(QSizePolicy.Policy.Expanding, table_policy)
        plan_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
            if size == 4
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )


def refresh_phase14_presentation(page) -> None:
    """Reassert the visible Phase 14 shell after legacy Comp Builder refreshes."""
    size = 4 if getattr(page, "_comp_group_size", 12) == 4 else 12
    _apply_plan_geometry(page, size)
    table = getattr(page, "comp_phase14_plan_table", None)
    if table is not None:
        table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
            if size == 12
            else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
    _refresh_shell(page)


def _set_group_size(page, size: int) -> None:
    from ui import comp_builder_roster_intake_support as intake

    page._comp_group_size = size
    page._comp_roster_member_by_slot = {}
    intake._load_roster_shape(page, size)

    # The roster helper still owns legacy 4/12 matrix sizing. The Phase 14 shell
    # owns visible geometry, so reassert the compact/expanding presentation.
    _apply_plan_geometry(page, size)
    _refresh_shell(page)


def _generate_plan(page) -> None:
    from ui import comp_builder_build_candidate_support as candidate_support

    candidate_support._apply_best_candidates_to_all(page)
    _refresh_shell(page)


def _build_brief(page) -> QWidget:
    host = QWidget()
    host.setProperty("compRaidBrief", True)
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)

    team_size_host = QWidget()
    team_size_layout = QVBoxLayout(team_size_host)
    team_size_layout.setContentsMargins(0, 0, 0, 0)
    team_size_layout.setSpacing(2)
    team_size_label = QLabel("TEAM SIZE")
    team_size_label.setProperty("sidebarHeading", True)
    team_size_buttons = QWidget()
    team_size_buttons_layout = QHBoxLayout(team_size_buttons)
    team_size_buttons_layout.setContentsMargins(0, 0, 0, 0)
    team_size_buttons_layout.setSpacing(0)
    page.comp_phase14_group_buttons = QButtonGroup(page)
    page.comp_phase14_group_buttons.setExclusive(True)
    for size in (4, 12):
        button = QPushButton(str(size))
        button.setCheckable(True)
        button.setProperty("compTeamSize", True)
        button.setFixedWidth(48)
        button.clicked.connect(lambda _checked=False, size=size: _set_group_size(page, size))
        page.comp_phase14_group_buttons.addButton(button, size)
        team_size_buttons_layout.addWidget(button)
    selected_size = 4 if getattr(page, "_comp_group_size", 12) == 4 else 12
    selected_button = page.comp_phase14_group_buttons.button(selected_size)
    if selected_button is not None:
        selected_button.setChecked(True)
    team_size_layout.addWidget(team_size_label)
    team_size_layout.addWidget(team_size_buttons)
    row.addWidget(team_size_host)

    _rehome(page.goal_combo, row)
    goal_host = _context_box("TRIAL", page.goal_combo)
    row.removeWidget(page.goal_combo)
    row.addWidget(goal_host, 2)

    _rehome(page.difficulty_combo, row)
    difficulty_host = _context_box("DIFFICULTY", page.difficulty_combo)
    row.removeWidget(page.difficulty_combo)
    row.addWidget(difficulty_host, 2)

    _rehome(page.plan_name_input, row)
    name_host = _context_box("PLAN NAME", page.plan_name_input)
    row.removeWidget(page.plan_name_input)
    row.addWidget(name_host, 2)

    style = getattr(page, "comp_composition_style_combo", None)
    if style is not None:
        _rehome(style, row)
        style_host = _context_box("PLAN STYLE", style)
        row.removeWidget(style)
        row.addWidget(style_host, 2)

    load_team = getattr(page, "comp_load_team_button", None)
    if load_team is not None:
        load_team.setText("Load Players")
        load_team.setToolTip(
            "Load or paste the players for this plan. This fills player/chair context; "
            "it does not choose builds."
        )
        _rehome(load_team, row)

    generate = getattr(page, "apply_all_comp_candidates_button", None)
    if generate is not None:
        generate.setText("Auto-Fill Builds")
        generate.setProperty("primary", True)
        generate.setToolTip(
            "Fill unresolved chairs with the best eligible build/gear recommendation "
            "while preserving choices already made."
        )
        try:
            generate.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        generate.clicked.connect(lambda *_: _generate_plan(page))
        _rehome(generate, row)

    return host


def _build_plan_table(page, card: FoundryCard) -> None:
    page.matrix_table.hide()

    table = QTableWidget(0, len(PRESENTATION_HEADERS))
    table.setHorizontalHeaderLabels(PRESENTATION_HEADERS)
    table.setProperty("compRecommendedPlanTable", True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(31)
    table.setAlternatingRowColors(False)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setMinimumHeight(500)
    table.setMaximumHeight(MAX_WIDGET_HEIGHT)
    table.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
    table.cellClicked.connect(lambda row, column: _select_plan_row(page, row, column))
    table.currentCellChanged.connect(
        lambda current_row, _current_col, _prev_row, _prev_col: _select_plan_row(page, current_row)
    )
    page.comp_phase14_plan_table = table
    card.body_layout.addWidget(table)


def _why_section_frame(kind: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setProperty("compWhySection", True)
    frame.setProperty("whySectionKind", kind)
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(5)
    return frame, layout


def _build_why(page, card: FoundryCard) -> None:
    for child in card.body.findChildren(QWidget):
        child.hide()

    host = QWidget()
    host.setProperty("compWhyPlanBody", True)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(2, 0, 2, 0)
    layout.setSpacing(10)

    page.comp_phase14_why_header = QLabel("Select a player")
    page.comp_phase14_why_header.setProperty("sidebarHeading", True)
    card.set_header_action(page.comp_phase14_why_header)

    recommendation_title = QLabel("RECOMMENDATION")
    recommendation_title.setProperty("sidebarHeading", True)
    layout.addWidget(recommendation_title)

    recommendation_frame, recommendation_layout = _why_section_frame("recommendation")
    recommendation_frame.setProperty("compCandidateChoice", True)
    recommendation_frame.mousePressEvent = (
        lambda event, frame=recommendation_frame: _apply_choice(page, frame)
    )
    page.comp_phase14_recommendation_frame = recommendation_frame

    confidence_row = QHBoxLayout()
    confidence_row.setContentsMargins(0, 0, 0, 0)
    confidence_row.addStretch(1)
    page.comp_phase14_confidence = QLabel("Evidence pending")
    page.comp_phase14_confidence.setProperty("compPlanConfidence", True)
    page.comp_phase14_confidence.setProperty("confidenceBadge", True)
    page.comp_phase14_confidence.setAlignment(
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    )
    confidence_row.addWidget(page.comp_phase14_confidence, 0)
    recommendation_layout.addLayout(confidence_row)

    set_row = QHBoxLayout()
    set_row.setContentsMargins(0, 2, 0, 2)
    set_row.setSpacing(10)

    set_one_frame, set_one_layout = _why_section_frame("recommendedSet")
    page.comp_phase14_set_one = QLabel("No recommendation")
    page.comp_phase14_set_one.setWordWrap(True)
    page.comp_phase14_set_one.setProperty("compRecommendedSetName", True)
    set_one_layout.addWidget(page.comp_phase14_set_one)
    set_one_count = QLabel("5 pieces")
    set_one_count.setProperty("compRecommendedSetCount", True)
    set_one_layout.addWidget(set_one_count)

    page.comp_phase14_set_plus = QLabel("+")
    page.comp_phase14_set_plus.setProperty("compRecommendedSetPlus", True)
    page.comp_phase14_set_plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
    page.comp_phase14_set_plus.setFixedWidth(24)

    set_two_frame, set_two_layout = _why_section_frame("recommendedSet")
    page.comp_phase14_set_two = QLabel("")
    page.comp_phase14_set_two.setWordWrap(True)
    page.comp_phase14_set_two.setProperty("compRecommendedSetName", True)
    set_two_layout.addWidget(page.comp_phase14_set_two)
    set_two_count = QLabel("5 pieces")
    set_two_count.setProperty("compRecommendedSetCount", True)
    set_two_layout.addWidget(set_two_count)

    set_row.addWidget(set_one_frame, 1)
    set_row.addWidget(page.comp_phase14_set_plus, 0, Qt.AlignmentFlag.AlignCenter)
    set_row.addWidget(set_two_frame, 1)
    recommendation_layout.addLayout(set_row)

    page.comp_phase14_role_footer = QLabel("No role selected")
    page.comp_phase14_role_footer.setProperty("compRecommendationRoleFooter", True)
    recommendation_layout.addWidget(page.comp_phase14_role_footer)

    # Retained as a compact accessible summary for tests/tooltips and any consumers
    # that already read the recommendation label.
    page.comp_phase14_recommendation = QLabel("No recommendation available.")
    page.comp_phase14_recommendation.setVisible(False)
    page.comp_phase14_recommendation.setProperty("compPlanRecommendation", True)

    layout.addWidget(recommendation_frame)

    why_title = QLabel("WHY")
    why_title.setProperty("sidebarHeading", True)
    layout.addWidget(why_title)

    why_frame, why_layout = _why_section_frame("why")
    page.comp_phase14_why_text = QLabel()
    page.comp_phase14_why_text.setWordWrap(True)
    page.comp_phase14_why_text.setProperty("compPlanWhyText", True)
    why_layout.addWidget(page.comp_phase14_why_text)

    page.comp_phase14_refresh_sources = QPushButton("Load Current Ranked Builds")
    page.comp_phase14_refresh_sources.setProperty("primary", True)
    page.comp_phase14_refresh_sources.setToolTip(
        "Fetch current ranked-team build evidence for this trial and use it as Recruit build options."
    )
    page.comp_phase14_refresh_sources.setVisible(False)

    def refresh_ranked_builds() -> None:
        source_button = getattr(page, "refresh_esologs_button", None)
        if source_button is None:
            page.status.warning("Current ranked build evidence is unavailable on this page.")
            return
        source_button.click()

    page.comp_phase14_refresh_sources.clicked.connect(refresh_ranked_builds)
    why_layout.addWidget(page.comp_phase14_refresh_sources)
    layout.addWidget(why_frame)

    alt_title = QLabel("ALTERNATIVES")
    alt_title.setProperty("sidebarHeading", True)
    layout.addWidget(alt_title)

    alt_one_frame, alt_one_layout = _why_section_frame("alternative")
    alt_one_frame.setProperty("compCandidateChoice", True)
    alt_one_frame.mousePressEvent = (
        lambda event, frame=alt_one_frame: _apply_choice(page, frame)
    )
    page.comp_phase14_alt_one_frame = alt_one_frame
    page.comp_phase14_alt_one = QLabel()
    page.comp_phase14_alt_one.setWordWrap(True)
    page.comp_phase14_alt_one.setProperty("compPlanAlternative", True)
    alt_one_layout.addWidget(page.comp_phase14_alt_one)
    layout.addWidget(alt_one_frame)

    alt_two_frame, alt_two_layout = _why_section_frame("alternative")
    alt_two_frame.setProperty("compCandidateChoice", True)
    alt_two_frame.mousePressEvent = (
        lambda event, frame=alt_two_frame: _apply_choice(page, frame)
    )
    if not hasattr(page, "_comp_manual_gear_sets_by_slot"):
        page._comp_manual_gear_sets_by_slot = {}
    page.comp_phase14_alt_two_frame = alt_two_frame
    page.comp_phase14_alt_two = QLabel()
    page.comp_phase14_alt_two.setWordWrap(True)
    page.comp_phase14_alt_two.setProperty("compPlanAlternative", True)
    alt_two_layout.addWidget(page.comp_phase14_alt_two)
    layout.addWidget(alt_two_frame)

    page.comp_phase14_set_picker_host = QWidget()
    page.comp_phase14_set_picker_layout = QVBoxLayout(page.comp_phase14_set_picker_host)
    page.comp_phase14_set_picker_layout.setContentsMargins(0, 4, 0, 4)
    page.comp_phase14_set_picker_layout.setSpacing(6)
    page.comp_phase14_set_picker_host.setVisible(False)
    layout.addWidget(page.comp_phase14_set_picker_host)

    for choice_frame in (
        recommendation_frame,
        alt_one_frame,
        alt_two_frame,
    ):
        choice_frame._comp_candidate = None
        _set_choice_state(choice_frame, selected=False, enabled=False)

    info_frame, info_layout = _why_section_frame("info")
    info_row = QHBoxLayout()
    info_row.setContentsMargins(0, 0, 0, 0)
    info_row.setSpacing(8)
    info_icon = QLabel("i")
    info_icon.setProperty("compWhyInfoIcon", True)
    info_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    info_icon.setFixedSize(22, 22)
    info_text = QLabel(
        "Alternatives are evidence-backed options. Choose based on team coverage, "
        "available gear, and progression needs."
    )
    info_text.setWordWrap(True)
    info_text.setProperty("compWhyInfoText", True)
    info_row.addWidget(info_icon, 0, Qt.AlignmentFlag.AlignTop)
    info_row.addWidget(info_text, 1)
    info_layout.addLayout(info_row)
    layout.addWidget(info_frame)
    layout.addStretch(1)

    card.body_layout.addWidget(host)
    host.show()


def _materialize_visible_recommendations(page) -> int:
    """Commit each chair's visible recommendation unless the user chose another candidate."""
    from ui import comp_builder_build_candidate_support as candidate_support

    applied = getattr(page, "_comp_applied_candidates", {})
    committed = 0
    for row in range(page.matrix_table.rowCount()):
        slot_name = page._cell_text(row, 0) or f"Slot {row + 1}"
        if slot_name in applied:
            continue
        try:
            candidates = tuple(candidate_support._chair_candidates(page, row))
        except (AttributeError, OSError, TypeError, ValueError):
            candidates = ()
        if not candidates:
            continue
        candidate_support._set_candidate_for_row(page, row, candidates[0])
        committed += 1
    return committed


def _mark_comp_state_dirty(page) -> None:
    state = getattr(page, "_comp_plan_state", None)
    if state is None or getattr(state, "dirty", False):
        return
    from dataclasses import replace
    page._comp_plan_state = replace(state, dirty=True)


def _sync_context_into_comp_state(page) -> None:
    state = getattr(page, "_comp_plan_state", None)
    if state is None:
        return

    from dataclasses import replace
    from ui.comp_builder_page import GOAL_TRIALS

    goal = str(page.goal_combo.currentText() or "").strip()
    trial = str(GOAL_TRIALS.get(goal, state.trial_id) or state.trial_id).strip()
    name = str(page.plan_name_input.text() or "").strip() or state.raid_plan_name
    difficulty = str(page.difficulty_combo.currentText() or "").strip() or state.difficulty
    page._comp_plan_state = replace(
        state,
        raid_plan_name=name,
        trial_id=trial,
        difficulty=difficulty,
        achievement_goal=goal or state.achievement_goal,
        dirty=True,
    )


def _reload_bound_raid_plan(page) -> bool:
    state = getattr(page, "_comp_plan_state", None)
    if state is None:
        return False

    plan_id = str(state.raid_plan_id or "").strip()
    combo = getattr(page, "plan_name_input", None)
    if combo is None or not hasattr(combo, "findData"):
        return False
    index = combo.findData(plan_id)
    if index < 0:
        refresh = getattr(page, "_refresh_raid_plan_name_choices", None)
        if callable(refresh):
            refresh()
            index = combo.findData(plan_id)
    if index < 0:
        return False

    loader = getattr(page, "_raid_plan_name_selected", None)
    if not callable(loader):
        return False
    loader(index)
    return True


def _save_to_originating_raid_plan(page) -> bool:
    """Save current Comp choices without silently applying recommendations.

    Raid Plan-bound sessions persist canonical CompPlanState directly. The generated
    draft path remains only as a compatibility fallback for ad-hoc/unbound sessions.
    """
    try:
        window = page.window()
        _sync_context_into_comp_state(page)
        state = getattr(page, "_comp_plan_state", None)
        if state is not None:
            persist_state = getattr(window, "_persist_comp_plan_state_to_raid_plan", None)
            if not callable(persist_state):
                page.status.error("Canonical Raid Plan save bridge is unavailable.")
                return
            plan = persist_state(navigate=False)
        else:
            from ui import comp_builder_build_candidate_support as candidate_support

            draft = candidate_support.save_generated_plan(page)
            persist_legacy = getattr(
                window,
                "_persist_generated_comp_plan_to_raid_plan",
                None,
            )
            if not callable(persist_legacy):
                page.status.error("Legacy Comp save bridge is unavailable.")
                return
            plan = persist_legacy(draft.name, navigate=False)
    except Exception as exc:
        page.status.error(
            f"Could not save Comp Builder plan: {type(exc).__name__}: {exc}"
        )
        return

    if plan is not None:
        page._raid_plan_origin_id = plan.plan_id
        refresh_names = getattr(page, "_refresh_raid_plan_name_choices", None)
        if callable(refresh_names):
            refresh_names()
            page.plan_name_input.setText(plan.name)
        page.status.success(f"Saved Comp Builder changes to Raid Plan: {plan.name}.")
        return True
    return False


def _has_pending_changes(page) -> bool:
    state = getattr(page, "_comp_plan_state", None)
    return bool(state is not None and getattr(state, "dirty", False))


def _save_pending_changes(page) -> bool:
    if not _has_pending_changes(page):
        return True
    return bool(_save_to_originating_raid_plan(page))


def _discard_pending_changes(page) -> None:
    if not _has_pending_changes(page):
        return
    if not _reload_bound_raid_plan(page):
        page.status.warning("Could not reload the bound Raid Plan to discard Comp changes.")


def _build_health(page, card: FoundryCard) -> None:
    for child in card.body.findChildren(QWidget):
        child.hide()

    body = QWidget()
    body.setProperty("compTeamHealthBody", True)
    row = QHBoxLayout(body)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)

    tiles = (
        ("COVERED", "✓", "covered", "comp_phase14_health_covered", "comp_phase14_health_covered_detail"),
        ("MISSING", "×", "missing", "comp_phase14_health_missing", "comp_phase14_health_missing_detail"),
        ("DUPLICATE", "!", "duplicate", "comp_phase14_health_duplicate", "comp_phase14_health_duplicate_detail"),
        ("RECRUIT NEED", "i", "recruit", "comp_phase14_health_recruit", "comp_phase14_health_recruit_detail"),
    )
    for title, symbol, state, value_name, detail_name in tiles:
        tile, value, detail = _health_tile(title, symbol, state)
        setattr(page, value_name, value)
        setattr(page, detail_name, detail)
        row.addWidget(tile, 1)

    divider = QFrame()
    divider.setFrameShape(QFrame.Shape.VLine)
    row.addWidget(divider)

    save = getattr(page, "save_template_button", None)
    if save is not None:
        save.setText("Save Plan")
        try:
            save.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        save.clicked.connect(lambda *_: _save_to_originating_raid_plan(page))
        _rehome(save, row)

    send = getattr(page, "send_button", None)
    if send is not None:
        send.setText("Send to Raid Plan")
        send.setProperty("primary", True)
        _rehome(send, row)

    card.body_layout.addWidget(body)
    body.show()


def _install_shell(page) -> None:
    root = _workspace_root(page)
    matrix = _card_any(page, "Team", "Composition Matrix")
    details = _card_any(
        page,
        "Selected Player / Build Recommendation",
        "Selected Chair Setup & Evidence",
        "Composition Details & Summary",
    )
    coverage = _card_any(page, "Team Health", "Group Buff & Provider Coverage")
    actions = _card_any(page, "Actions")
    evidence = _card_any(page, "Evidence & Provenance")
    if root is None or matrix is None or details is None or coverage is None:
        return

    _detach_layout(root)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(10)

    page.header.subtitle.setText("Plan the team. Fill the gaps. Clear the content.")
    page.header.department.setText("FOUNDRYDOCK • RAID ENGINE")

    brief = _build_brief(page)
    page.comp_phase14_raid_brief = brief
    root.addWidget(brief)

    matrix.set_title("Recommended Team Plan")
    matrix.setProperty("compRecommendedTeamPlan", True)
    matrix.setMinimumHeight(520)
    matrix.setMaximumHeight(MAX_WIDGET_HEIGHT)
    matrix.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )
    page.comp_phase14_plan_card = matrix
    _build_plan_table(page, matrix)

    details.set_title("Why This Plan")
    details.setProperty("compWhyThisPlan", True)
    details.setMinimumHeight(520)
    details.setMaximumHeight(MAX_WIDGET_HEIGHT)
    details.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Expanding,
    )
    page.comp_phase14_why_card = details
    _build_why(page, details)

    middle = QHBoxLayout()
    middle.setContentsMargins(0, 0, 0, 0)
    middle.setSpacing(10)
    middle.addWidget(matrix, 5)
    middle.addWidget(details, 3)
    root.addLayout(middle, 1)

    _apply_plan_geometry(
        page,
        4 if getattr(page, "_comp_group_size", 12) == 4 else 12,
    )

    coverage.set_title("Team Health")
    coverage.setProperty("compTeamHealth", True)
    coverage.setMinimumHeight(135)
    coverage.setMaximumHeight(170)
    _build_health(page, coverage)
    root.addWidget(coverage)

    if actions is not None:
        actions.hide()
    if evidence is not None:
        evidence.hide()
    provider_workload = _card_any(page, "Provider Rotation Workload")
    if provider_workload is not None:
        provider_workload.hide()
    load_template = getattr(page, "load_template_button", None)
    if load_template is not None:
        load_template.hide()
    refresh_sources = getattr(page, "refresh_esologs_button", None)
    if refresh_sources is not None:
        refresh_sources.hide()
    page.matrix_table.hide()

    page.workspace_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    page._comp_phase14_selected_backend_row = 0
    page.has_pending_changes = lambda: _has_pending_changes(page)
    page.save_pending_changes = lambda: _save_pending_changes(page)
    page.discard_pending_changes = lambda: _discard_pending_changes(page)
    _refresh_shell(page)

    page.goal_combo.currentTextChanged.connect(
        lambda *_: (_mark_comp_state_dirty(page), _refresh_shell(page))
    )
    page.difficulty_combo.currentTextChanged.connect(
        lambda *_: (_mark_comp_state_dirty(page), _refresh_shell(page))
    )
    plan_name = getattr(page, "plan_name_input", None)
    if plan_name is not None:
        edit_signal = getattr(plan_name, "editTextChanged", None)
        if edit_signal is not None:
            edit_signal.connect(lambda *_: _mark_comp_state_dirty(page))
    picker = getattr(page, "comp_candidate_choice_combo", None)
    if picker is not None:
        picker.currentIndexChanged.connect(lambda *_: _refresh_shell(page))


def _init_with_phase14_shell(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_shell(self)


def _render_slots_with_phase14_shell(self, slots) -> None:
    assert _ORIGINAL_RENDER_SLOTS is not None
    _ORIGINAL_RENDER_SLOTS(self, slots)

    # Roster/Raid Plan intake can own an explicit class requirement for a Recruit
    # chair. Reapply that chair-level constraint after every later matrix rebuild.
    try:
        from ui.comp_builder_roster_intake_support import _reapply_class_constraints
        _reapply_class_constraints(self)
    except (AttributeError, TypeError, ValueError):
        pass

    if hasattr(self, "comp_phase14_plan_table"):
        _refresh_shell(self)


def install() -> None:
    global _INSTALLED, _ORIGINAL_COMP_INIT, _ORIGINAL_RENDER_SLOTS
    global _ORIGINAL_REFRESH_CANDIDATES, _ORIGINAL_APPLY_ROSTER_CONTEXT
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    from ui import comp_builder_build_candidate_support as candidate_support

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    CompBuilderPage.__init__ = _init_with_phase14_shell

    _ORIGINAL_RENDER_SLOTS = CompBuilderPage._render_slots
    CompBuilderPage._render_slots = _render_slots_with_phase14_shell

    _ORIGINAL_REFRESH_CANDIDATES = candidate_support._refresh_candidates

    def refresh_candidates_with_shell(page) -> None:
        assert _ORIGINAL_REFRESH_CANDIDATES is not None
        _ORIGINAL_REFRESH_CANDIDATES(page)
        if hasattr(page, "comp_phase14_plan_table"):
            _refresh_shell(page)

    candidate_support._refresh_candidates = refresh_candidates_with_shell

    if hasattr(CompBuilderPage, "apply_roster_team_context"):
        _ORIGINAL_APPLY_ROSTER_CONTEXT = CompBuilderPage.apply_roster_team_context

        def apply_roster_context_with_shell(self, *args, **kwargs) -> None:
            assert _ORIGINAL_APPLY_ROSTER_CONTEXT is not None
            _ORIGINAL_APPLY_ROSTER_CONTEXT(self, *args, **kwargs)
            try:
                from ui.comp_builder_roster_intake_support import _reapply_class_constraints
                _reapply_class_constraints(self)
            except (AttributeError, TypeError, ValueError):
                pass
            _refresh_shell(self)

        CompBuilderPage.apply_roster_team_context = apply_roster_context_with_shell

    _INSTALLED = True
