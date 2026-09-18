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
    if not player or player.casefold().startswith("recruit"):
        return "Needs gear"
    slot = page._cell_text(row, 0) or f"Slot {row + 1}"
    applied = slot in getattr(page, "_comp_applied_candidates", {})
    if candidate is None:
        return "Needs build"
    if applied and bool(getattr(candidate, "complete_build", False)):
        return "Ready"
    if applied:
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
            player = page._cell_text(backend_row, 11) or "Recruit"
            role = page._cell_text(backend_row, 1) or "Unresolved"
            selected_class = page._selected_class(backend_row) or "Any class"
            role_class = role if selected_class == "Any class" else f"{role} • {selected_class}"
            values = (
                str(backend_row + 1),
                player,
                role_class,
                _candidate_label(candidate),
                _responsibility_for_row(page, backend_row),
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
        return

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


def _refresh_health(page) -> None:
    if not hasattr(page, "comp_phase14_health_covered"):
        return
    try:
        from ui import comp_builder_polish_support as polish
        from ui import team_progress_support
        from ui.components.team_progress_panels import coverage_from_declared_text

        declared = coverage_from_declared_text(team_progress_support._comp_declared_rows(page))
        applied = getattr(page, "_comp_applied_candidates", {}) or {}
        assigned = polish.coverage_from_candidate_rows(tuple(applied.items()))
        merged = polish.merge_coverage(assigned, declared)
    except (AttributeError, ImportError, TypeError, ValueError):
        merged = ()

    covered = [item for item in merged if item.covered]
    missing = [item for item in merged if not item.covered]
    total = len(merged)
    page.comp_phase14_health_covered.setText(f"Covered {len(covered)} / {total}" if total else "Coverage unresolved")
    page.comp_phase14_health_covered_detail.setText("Major buffs & debuffs")

    first_missing = missing[0].name if missing else "None"
    page.comp_phase14_health_missing.setText(first_missing)
    page.comp_phase14_health_missing_detail.setText(
        "No source in current plan" if missing else "No tracked gaps"
    )

    set_counts: Counter[str] = Counter()
    for candidate in (getattr(page, "_comp_applied_candidates", {}) or {}).values():
        for gear in tuple(getattr(candidate, "gear_sets", ()) or ()):
            if gear:
                set_counts[str(gear)] += 1
    duplicates = [name for name, count in set_counts.items() if count > 1]
    page.comp_phase14_health_duplicate.setText(duplicates[0] if duplicates else "None")
    page.comp_phase14_health_duplicate_detail.setText(
        "Already covered by another player" if duplicates else "No duplicated tracked set"
    )

    recruits: list[tuple[str, str]] = []
    for row in range(page.matrix_table.rowCount()):
        player = page._cell_text(row, 11).strip()
        if not player or player.casefold().startswith("recruit"):
            role = page._cell_text(row, 1) or "Open role"
            selected_class = page._selected_class(row)
            need = role if selected_class == "Any class" else f"{selected_class} {role}"
            recruits.append((player or "Recruit", need))
    if recruits:
        page.comp_phase14_health_recruit.setText(recruits[0][1])
        page.comp_phase14_health_recruit_detail.setText(
            f"{len(recruits)} Recruit slot(s) need gear / setup"
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
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
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
        load_team.setText("Load Team")
        _rehome(load_team, row)

    generate = getattr(page, "apply_all_comp_candidates_button", None)
    if generate is not None:
        generate.setText("Generate Team Plan")
        generate.setProperty("primary", True)
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
    page.comp_phase14_alt_two_frame = alt_two_frame
    page.comp_phase14_alt_two = QLabel()
    page.comp_phase14_alt_two.setWordWrap(True)
    page.comp_phase14_alt_two.setProperty("compPlanAlternative", True)
    alt_two_layout.addWidget(page.comp_phase14_alt_two)
    layout.addWidget(alt_two_frame)

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


def _save_to_originating_raid_plan(page) -> None:
    """Save the current Comp Builder choices back into the bound Raid Plan."""
    origin_id = str(getattr(page, "_raid_plan_origin_id", "") or "").strip()
    if not origin_id:
        page.status.warning(
            "This Comp Builder session is not bound to a Raid Plan. "
            "Open it from Raid Plan first, then Save Plan will update that run."
        )
        return

    from ui import comp_builder_build_candidate_support as candidate_support

    draft = candidate_support.save_generated_plan(page)
    window = page.window()
    persist = getattr(window, "_persist_generated_comp_plan_to_raid_plan", None)
    if not callable(persist):
        page.status.error("Raid Plan save bridge is unavailable.")
        return

    plan = persist(draft.name, navigate=False)
    if plan is not None:
        page.status.success(f"Saved Comp Builder changes to Raid Plan: {plan.name}.")


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
    _refresh_shell(page)

    page.goal_combo.currentTextChanged.connect(lambda *_: _refresh_shell(page))
    page.difficulty_combo.currentTextChanged.connect(lambda *_: _refresh_shell(page))
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
            _refresh_shell(self)

        CompBuilderPage.apply_roster_team_context = apply_roster_context_with_shell

    _INSTALLED = True
