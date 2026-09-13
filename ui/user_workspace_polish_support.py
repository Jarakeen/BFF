from __future__ import annotations

"""Small user-facing polish for Rotation, Main overview, and Characters navigation."""

_INSTALLED = False


def _tab_index_by_text(tabs, title: str) -> int:
    wanted = str(title or "").strip().casefold()
    for index in range(tabs.count()):
        if str(tabs.tabText(index) or "").strip().casefold() == wanted:
            return index
    return -1


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.main_window import MainWindow
    from ui.operations_console import OperationsConsole
    from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage
    from widgets.roster_record import RosterRecord

    # Rotation: show practical examples as ghost text without silently supplying
    # canonical evidence. The spin boxes stay at their explicit unresolved value
    # until the user actually enters a number.
    rotation_init = CanonicalRotationDashboardPage.__init__

    def rotation_init_with_hints(self, *args, **kwargs) -> None:
        rotation_init(self, *args, **kwargs)

        target_resist = getattr(self, "rotation_dd_target_resistance_spin", None)
        if target_resist is not None:
            target_resist.setSpecialValueText("")
            line_edit = target_resist.lineEdit()
            if line_edit is not None:
                line_edit.setPlaceholderText("18,200 armor (typical PvE)")

        recovery_trigger = getattr(self, "rotation_recovery_trigger_spin", None)
        if recovery_trigger is not None:
            recovery_trigger.setSpecialValueText("")
            line_edit = recovery_trigger.lineEdit()
            if line_edit is not None:
                line_edit.setPlaceholderText("35% suggested")

    CanonicalRotationDashboardPage.__init__ = rotation_init_with_hints

    # Main overview: Character Command should be a normal card. The old explicit
    # overviewAccent property is what paints the bright left-edge stripe.
    player_card = OperationsConsole._player_card

    def player_card_without_accent(self, build):
        card = player_card(self, build)
        card.setProperty("overviewAccent", None)
        card.style().unpolish(card)
        card.style().polish(card)
        return card

    OperationsConsole._player_card = player_card_without_accent

    # Personnel record: make the account identity clear without replacing the
    # existing PlayerName persistence field.
    record_init = RosterRecord.__init__

    def record_init_with_gamertag_hint(self, *args, **kwargs) -> None:
        record_init(self, *args, **kwargs)
        self.player_name.setPlaceholderText("Gamertag")

    RosterRecord.__init__ = record_init_with_gamertag_hint

    # Sidebar Characters is a focused doorway into the shared Roster workspace.
    # Open the tab by label so later tab reordering cannot quietly break it.
    show_page = MainWindow.show_page

    def show_page_with_personnel_default(self, page_name: str):
        result = show_page(self, page_name)
        if page_name == "characters":
            roster_page = self.pages.get("roster_page")
            tabs = getattr(roster_page, "tabs", None)
            if tabs is not None:
                personnel_index = _tab_index_by_text(tabs, "PERSONNEL")
                if personnel_index >= 0:
                    tabs.setCurrentIndex(personnel_index)
        return result

    MainWindow.show_page = show_page_with_personnel_default
    _INSTALLED = True


__all__ = ["install"]
