from __future__ import annotations

"""Carry roster-owned player/class/role context into Comp Maker without inventing builds."""

from PySide6.QtWidgets import QComboBox, QHeaderView, QTableWidgetItem


_INSTALLED = False
PLAYER_COLUMN = 11


def _role_key(value: object) -> str:
    text = " ".join(str(value or "").strip().casefold().split())
    if "tank" in text:
        return "tank"
    if "heal" in text:
        return "healer"
    if "damage" in text or "dps" in text:
        return "damage"
    # Comp Maker's canonical flexible damage chairs are labelled simply "DD".
    # Roster roles can also be things like "Support DD" or "Zenkosh DD".
    words = text.replace("/", " ").replace("-", " ").split()
    if "dd" in words:
        return "damage"
    return ""


def _row_role(page, row: int) -> str:
    return _role_key(page._cell_text(row, 1))


def _player_label(member) -> str:
    player = str(getattr(member, "PlayerName", "") or "").strip()
    character = str(getattr(member, "CharacterName", "") or "").strip()
    if player and character:
        return f"{player} • {character}"
    return player or character or "Unnamed"


def _ensure_player_column(page) -> None:
    table = page.matrix_table
    if table.columnCount() <= PLAYER_COLUMN:
        table.setColumnCount(PLAYER_COLUMN + 1)
    header_item = table.horizontalHeaderItem(PLAYER_COLUMN)
    if header_item is None:
        header_item = QTableWidgetItem("PLAYER")
        table.setHorizontalHeaderItem(PLAYER_COLUMN, header_item)
    else:
        header_item.setText("PLAYER")
    table.horizontalHeader().setSectionResizeMode(
        PLAYER_COLUMN, QHeaderView.ResizeMode.Stretch
    )


def _set_player(page, row: int, member) -> None:
    _ensure_player_column(page)
    item = page.matrix_table.item(row, PLAYER_COLUMN)
    if item is None:
        item = QTableWidgetItem()
        page.matrix_table.setItem(row, PLAYER_COLUMN, item)
    item.setText(_player_label(member))
    item.setToolTip(
        "Roster player carried into Comp Maker. This does not imply a saved build exists."
    )

    eso_class = str(getattr(member, "EsoClass", "") or "").strip()
    class_combo = page.matrix_table.cellWidget(row, 2)
    if isinstance(class_combo, QComboBox) and eso_class:
        index = class_combo.findText(eso_class)
        if index >= 0:
            class_combo.setCurrentIndex(index)


def _clear_player_rows(page) -> None:
    _ensure_player_column(page)
    for row in range(page.matrix_table.rowCount()):
        item = page.matrix_table.item(row, PLAYER_COLUMN)
        if item is None:
            item = QTableWidgetItem()
            page.matrix_table.setItem(row, PLAYER_COLUMN, item)
        item.setText("")


def _match_rows(page, members) -> list[tuple[int, object]]:
    """Place roster members into matching Comp Maker role chairs.

    Known-role players are placed first so an unresolved roster role cannot steal
    a Tank/Healer chair before a real Tank/Healer is processed. Within each role,
    roster order is preserved.
    """
    available = list(range(page.matrix_table.rowCount()))
    matches: list[tuple[int, object]] = []
    members = list(members)

    known = [member for member in members if _role_key(getattr(member, "PrimaryRole", ""))]
    unknown = [member for member in members if not _role_key(getattr(member, "PrimaryRole", ""))]

    for member in known:
        wanted = _role_key(getattr(member, "PrimaryRole", ""))
        row = next((r for r in available if _row_role(page, r) == wanted), None)
        if row is None:
            # More players of a role than the 2/2/8 skeleton supports: keep the
            # player visible in the next open chair rather than silently dropping them.
            row = available[0] if available else None
        if row is None:
            break
        available.remove(row)
        matches.append((row, member))

    for member in unknown:
        if not available:
            break
        row = available.pop(0)
        matches.append((row, member))

    return matches


def apply_roster_team_context(page, team_name: str, members) -> None:
    members = tuple(members)
    page._roster_team_context_name = str(team_name or "").strip()
    page._roster_team_context_member_ids = tuple(
        int(member.Id) for member in members if getattr(member, "Id", None) is not None
    )
    page._roster_team_context_members = members

    # Start with the neutral 2/2/8 skeleton. The roster supplies people/class/role;
    # Comp Maker still owns the job of finding or constructing builds for them.
    page._load_flexible(show_status=False)
    _clear_player_rows(page)

    matched = _match_rows(page, members)
    for row, member in matched:
        _set_player(page, row, member)

    if hasattr(page, "plan_name_input") and page._roster_team_context_name:
        page.plan_name_input.setText(page._roster_team_context_name)

    if hasattr(page, "_refresh_coverage"):
        page._refresh_coverage()

    role_counts = {"tank": 0, "healer": 0, "damage": 0, "unresolved": 0}
    for member in members:
        key = _role_key(getattr(member, "PrimaryRole", "")) or "unresolved"
        role_counts[key] += 1
    page.status.info(
        f"Loaded {len(matched)} roster player(s) from {page._roster_team_context_name or 'selected team'} "
        f"into Comp Maker: {role_counts['tank']} tank, {role_counts['healer']} healer, "
        f"{role_counts['damage']} DD, {role_counts['unresolved']} unresolved. "
        "Classes are carried over; empty builds remain intentionally unresolved."
    )


def _send_roster_team_to_comp(page) -> None:
    from ui import roster_assignment_action_support as assignment_actions

    team_name = assignment_actions._selected_team_name(page)
    if not team_name:
        page.status.warning("Choose a team in the Assignments team menu before sending it to Comp Maker.")
        return
    members = assignment_actions._team_members(page, team_name)
    if not members:
        page.status.warning(f"{team_name} has no roster members to send to Comp Maker.")
        return
    if not assignment_actions._show_page(page, "comp_builder"):
        return

    comp = getattr(page.window(), "pages", {}).get("comp_builder")
    if comp is None or not hasattr(comp, "apply_roster_team_context"):
        page.status.warning("Comp Maker opened, but the roster intake bridge is unavailable.")
        return
    comp.apply_roster_team_context(team_name, members)


def _flatten_attention_card(page) -> None:
    card = getattr(page, "attention_card", None)
    if card is None:
        return
    card.header.hide()
    card.setProperty("flatActionCard", True)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    from ui.themed_roster_page import RosterPage
    from ui import roster_assignment_action_support as assignment_actions

    original_init = CompBuilderPage.__init__

    def init_with_roster_intake(self, parent=None):
        original_init(self, parent)
        _ensure_player_column(self)

    CompBuilderPage.__init__ = init_with_roster_intake
    CompBuilderPage.apply_roster_team_context = apply_roster_team_context

    # Existing buttons resolve this module-level function at click time, so swap
    # the handler rather than rebuilding yet another button row.
    assignment_actions._send_to_comp_maker = _send_roster_team_to_comp

    original_refresh_summary_cards = RosterPage._refresh_summary_cards

    def refresh_summary_cards_flat(self):
        result = original_refresh_summary_cards(self)
        _flatten_attention_card(self)
        return result

    RosterPage._refresh_summary_cards = refresh_summary_cards_flat
    _INSTALLED = True
