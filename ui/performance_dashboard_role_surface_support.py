from __future__ import annotations

"""Final role-aware visibility for the polished Performance Dashboard.

The performance page is assembled by several compatibility/polish layers.  This
module intentionally installs last in the DD presentation chain and owns only the
final visible surface.  It does not fetch data and it does not touch local state.

For DPS snapshots the generic raid-support tracking controls are hidden so the
DD evidence cards are not buried under healer/tank context.  Healer and tank
snapshots retain the support controls.
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


def _apply_role_surface(page, snapshot) -> None:
    role = str(getattr(snapshot, "Role", "") or "").strip().casefold()
    is_dd = role == "dps"

    # Generic support controls are useful for healer/tank review but they were
    # visually dominating the DPS page and obscuring the diagnostics built for
    # damage dealers.
    for name in (
        "support_effects_card",
        "graph_effect_card",
        "_performance_tracking_card",
    ):
        card = getattr(page, name, None)
        if card is not None:
            card.setVisible(not is_dd)

    # These are the DD cards/sections that must remain visible on a DPS result.
    # Guard every attribute because the base dashboard can still be used without
    # the optional DD extensions in isolated tests/tools.
    for name in (
        "kpi_card",
        "dot_card",
        "dd_readout_card",
        "output_card",
        "abilities_card",
        "quick_read_card",
    ):
        card = getattr(page, name, None)
        if card is not None and is_dd:
            card.setVisible(True)

    # The old category-chart cards are compatibility objects only.  Never let a
    # later wrapper resurrect them on the polished DPS surface.
    if is_dd:
        for name in ("buff_card", "debuff_card", "raid_debuff_card"):
            card = getattr(page, name, None)
            if card is not None:
                card.setVisible(False)


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

    def show_snapshot_with_role_surface(self, snapshot):
        _ORIGINAL_SHOW_SNAPSHOT(self, snapshot)
        _apply_role_surface(self, snapshot)

    PerformanceDashboard.build_ui = build_ui_with_role_surface
    PerformanceDashboard.show_snapshot = show_snapshot_with_role_surface
    _INSTALLED = True
