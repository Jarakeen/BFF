from __future__ import annotations

"""Final role-aware visibility for the polished Performance Dashboard.

The performance page is assembled by several compatibility/polish layers. This
module intentionally installs last in the DD presentation chain and owns only the
final visible surface. It does not fetch data and it does not touch local state.

DPS views stay damage-focused and hide healer/tank support-summary controls,
including the Graph Effects group-buff selector. Healer and tank views retain the
broader support-tracking controls.
"""

from PySide6.QtWidgets import QLabel

from ui.components.foundry_card import FoundryCard

_INSTALLED = False
_ORIGINAL_BUILD_UI = None
_ORIGINAL_SHOW_SNAPSHOT = None
_ORIGINAL_ACTOR_SELECTED = None


_ROLE_ALIASES = {
    "dps": "DPS",
    "dd": "DPS",
    "damage": "DPS",
    "damage dealer": "DPS",
    "healer": "Healer",
    "heal": "Healer",
    "healing": "Healer",
    "tank": "Tank",
    "tanking": "Tank",
}


def _canonical_performance_role(role: str) -> str | None:
    """Return the dashboard's canonical role name without guessing unknown roles."""

    normalized = " ".join(
        str(role or "").strip().casefold().replace("_", " ").replace("-", " ").split()
    )
    return _ROLE_ALIASES.get(normalized)


def _card_with_title(page, title: str):
    wanted = str(title or "").strip().casefold()
    for card in page.findChildren(FoundryCard):
        label = getattr(card, "title_label", None)
        text = label.text().strip().casefold() if label is not None else ""
        if text == wanted:
            return card
    return None


def _label_with_text(page, text: str):
    wanted = str(text or "").strip().casefold()
    for label in page.findChildren(QLabel):
        if label.text().strip().casefold() == wanted:
            return label
    return None


def _capture_polished_role_cards(page) -> None:
    """Remember polished surfaces that were not stored as page attributes."""

    page._performance_tracking_card = _card_with_title(
        page, "Track Specific Buffs / Debuffs"
    )
    page._performance_effect_timeline_label = _label_with_text(page, "Effect timeline")


def _set_visible(page, names: tuple[str, ...], visible: bool) -> None:
    for name in names:
        widget = getattr(page, name, None)
        if widget is not None:
            widget.setVisible(visible)


def _apply_role_name_surface(page, role: str, *, has_snapshot: bool) -> None:
    """Apply the final visible surface for one canonical performance role.

    New member tabs exist before an ESO Logs snapshot does. Their persisted model
    defaults to DPS, so the UI must not temporarily present the healer/support
    surface just because a compatibility layer constructed a different first item.
    Once a fight actor or saved profile changes the role, the surface follows that
    selection immediately.
    """

    canonical_role = _canonical_performance_role(role)
    is_dd = canonical_role == "DPS"
    is_healer = canonical_role == "Healer"
    is_support = canonical_role in {"Healer", "Tank"}

    # Support tracking controls belong to healer/tank views. The exact-effect
    # timeline is embedded inside output_card, so its heading and widget must be
    # role-gated independently while DPS keeps the output graph itself visible.
    # A blank or unknown role remains neutral instead of inheriting stale support.
    _set_visible(
        page,
        (
            "support_effects_card",
            "_performance_tracking_card",
            "graph_effect_card",
            "_performance_effect_timeline_label",
            "effect_timeline_widget",
        ),
        is_support,
    )

    # Healer diagnostics are role-exclusive. The healer layer normally toggles
    # these itself, but this final layer deliberately repeats the boundary so a
    # later/earlier wrapper cannot leak healer cards into a DPS snapshot.
    _set_visible(
        page,
        (
            "healer_readout_card",
            "hot_card",
            "kpi_heal_crit",
            "kpi_heal_response",
            "kpi_heal_cadence",
        ),
        bool(has_snapshot and is_healer),
    )

    # DD-only diagnostics are likewise symmetrical. Generic result cards are left
    # to the dashboard's normal empty/snapshot plumbing.
    _set_visible(
        page,
        ("dot_card", "dd_readout_card", "quick_read_card"),
        bool(has_snapshot and is_dd),
    )

    if has_snapshot and is_dd:
        _set_visible(
            page,
            ("kpi_card", "output_card", "abilities_card"),
            True,
        )

    # These older support-oriented chart cards are not part of the final DD view.
    # Healer/tank wrappers may populate/show them for their own role afterward.
    if is_dd:
        _set_visible(
            page,
            ("buff_card", "debuff_card", "raid_debuff_card"),
            False,
        )


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


def _sync_actor_role_picker(page) -> str | None:
    """Sync the role picker from the selected actor without preserving stale state.

    ESO Logs/service adapters are expected to emit canonical role names, but older
    paths and fixtures may still supply common aliases or casing variants. A role
    mismatch must never leave the previous actor's Healer selection in place.
    """

    choice = page.selected_actor()
    if choice is None:
        return None

    picker = getattr(page, "role_override", None)
    if picker is None:
        return None

    canonical_role = _canonical_performance_role(getattr(choice, "Role", ""))
    if canonical_role is None:
        picker.setCurrentIndex(-1)
    else:
        picker.setCurrentText(canonical_role)

    return canonical_role


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_UI, _ORIGINAL_SHOW_SNAPSHOT, _ORIGINAL_ACTOR_SELECTED
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    _ORIGINAL_BUILD_UI = PerformanceDashboard.build_ui
    _ORIGINAL_SHOW_SNAPSHOT = PerformanceDashboard.show_snapshot
    _ORIGINAL_ACTOR_SELECTED = PerformanceDashboard._on_actor_selected

    def build_ui_with_role_surface(self):
        _ORIGINAL_BUILD_UI(self)
        _capture_polished_role_cards(self)

        picker = getattr(self, "role_override", None)
        if picker is not None:
            # PerformanceProfile defaults to DPS. Make the freshly-created UI
            # agree with that model before the user loads a fight.
            default_role = _canonical_performance_role(
                getattr(getattr(self, "_last_profile", None), "Role", "DPS")
            ) or "DPS"
            picker.setCurrentText(default_role)
            picker.currentTextChanged.connect(
                lambda _text, page=self: _apply_selected_role_surface(page)
            )
            _apply_selected_role_surface(self)

    def actor_selected_with_role_surface(self, index: int):
        _ORIGINAL_ACTOR_SELECTED(self, index)
        _sync_actor_role_picker(self)
        _apply_selected_role_surface(self)

    def show_snapshot_with_role_surface(self, snapshot):
        _ORIGINAL_SHOW_SNAPSHOT(self, snapshot)

        # Keep the picker and final surface aligned with the snapshot that was
        # actually built. This prevents compatibility wrappers from displaying a
        # stale role after the requested performance result has loaded.
        picker = getattr(self, "role_override", None)
        snapshot_role = _canonical_performance_role(getattr(snapshot, "Role", ""))
        if picker is not None:
            if snapshot_role is None:
                picker.setCurrentIndex(-1)
            else:
                picker.setCurrentText(snapshot_role)

        _apply_role_surface(self, snapshot)

    PerformanceDashboard.build_ui = build_ui_with_role_surface
    PerformanceDashboard._on_actor_selected = actor_selected_with_role_surface
    PerformanceDashboard.show_snapshot = show_snapshot_with_role_surface
    _INSTALLED = True
