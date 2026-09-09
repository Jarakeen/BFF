from __future__ import annotations

"""Final role-aware visibility for the polished Performance Dashboard.

The performance page is assembled by several compatibility/polish layers. This
module intentionally installs last in the DD presentation chain and owns only the
final visible surface. It does not fetch data and it does not touch local state.

For DPS views the generic support-summary cards are hidden so the DD evidence
cards are not buried under healer/tank context. The Graph Effects selector stays
visible for every role because it controls the effect lanes drawn on the output
graph. Healer and tank views retain the broader support-tracking controls.
"""

from ui.components.foundry_card import FoundryCard

_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_SHOW_SNAPSHOT = None


def _card_with_title(page, title: str):
    wanted = str(title or "").strip().casefold()
    for card in page.findChildren(FoundryCard):
        label = getattr(card, "title_label", None)
        text = label.text().strip().casefold() if label is not None else ""
        if text == wanted:
            return card
    return None


def _capture_polished_role_cards(page) -> None:
    """Remember polished cards that were not stored as page attributes."""

    page._performance_tracking_card = _card_with_title(
        page, "Track Specific Buffs / Debuffs"
    )


def _apply_role_name_surface(page, role: str, *, has_snapshot: bool) -> None:
    """Apply the visible role surface from either a picker or a loaded snapshot.

    New member tabs exist before an ESO Logs snapshot does. Their persisted model
    defaults to DPS, so the UI must not temporarily present the healer/support
    surface just because the polished role combo happens to be constructed with a
    different first item. Once a fight actor or saved profile changes the role,
    the surface follows that selection immediately.
    """

    normalized = str(role or "").strip().casefold()
    is_dd = normalized == "dps"

    # These are support-summary surfaces, not graph controls. Hide them for DD.
    for name in (
        "support_effects_card",
        "_performance_tracking_card",
    ):
        card = getattr(page, name, None)
        if card is not None:
            card.setVisible(not is_dd)

    # Graph Effects owns the on/off checkboxes for the buff/debuff lanes painted
    # over the output graph. It must remain visible for DPS too, otherwise the
    # graph can show effect lanes that the user has no way to toggle.
    graph_effect_card = getattr(page, "graph_effect_card", None)
    if graph_effect_card is not None:
        graph_effect_card.setVisible(True)

    # Result cards only make sense after a snapshot exists. Before that, keep the
    # polished dashboard's normal empty-state behavior instead of revealing blank
    # DD result cards merely because the role picker says DPS.
    if has_snapshot and is_dd:
        for name in (
            "kpi_card",
            "dot_card",
            "dd_readout_card",
            "output_card",
            "abilities_card",
            "quick_read_card",
        ):
            card = getattr(page, name, None)
            if card is not None:
                card.setVisible(True)

    if is_dd:
        for name in ("buff_card", "debuff_card", "raid_debuff_card"):
            card = getattr(page, name, None)
            if card is not None:
                card.setVisible(False)


def _apply_role_surface(page, snapshot) -> None:
    _apply_role_name_surface(
        page,
        str(getattr(snapshot, "Role", "") or ""),
        has_snapshot=True,
    )


def _apply_selected_role_surface(page) -> None:
    picker = getattr(page, "role_override", None)
    if picker is None:
        return
    _apply_role_name_surface(
        page,
        picker.currentText(),
        has_snapshot=getattr(page, "_last_snapshot", None) is not None,
    )


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI, _ORIGINAL_SHOW_SNAPSHOT
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    _ORIGINAL_BUILD_UI = PerformanceDashboard.build_ui
    _ORIGINAL_SHOW_SNAPSHOT = PerformanceDashboard.show_snapshot

    def build_ui_with_role_surface(self):
        _ORIGINAL_BUILD_UI(self)
        _capture_polished_role_cards(self)

        picker = getattr(self, "role_override", None)
        if picker is not None:
            # PerformanceProfile defaults to DPS. Make the freshly-created UI
            # agree with that model before the user loads a fight.
            default_role = str(getattr(getattr(self, "_last_profile", None), "Role", "DPS") or "DPS")
            picker.setCurrentText(default_role)
            picker.currentTextChanged.connect(
                lambda _text, page=self: _apply_selected_role_surface(page)
            )
            _apply_selected_role_surface(self)

    def show_snapshot_with_role_surface(self, snapshot):
        _ORIGINAL_SHOW_SNAPSHOT(self, snapshot)
        _apply_role_surface(self, snapshot)

    PerformanceDashboard.build_ui = build_ui_with_role_surface
    PerformanceDashboard.show_snapshot = show_snapshot_with_role_surface
    _INSTALLED = True
