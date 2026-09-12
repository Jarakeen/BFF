from __future__ import annotations

"""DD-specific presentation for the Performance Dashboard."""

from ui.theme.colors import Colors

_INSTALLED = False
_ORIGINAL_BUILD_KPI_CARD = None
_ORIGINAL_SHOW_SNAPSHOT = None
_ORIGINAL_UPDATE_ABILITIES = None


def _ability_value_text(percent: float, total: float) -> str:
    if abs(total) >= 1_000_000:
        total_text = f"{total / 1_000_000:.2f}m"
    elif abs(total) >= 1_000:
        total_text = f"{total / 1_000:.1f}k"
    else:
        total_text = f"{total:,.0f}"
    return f"{percent:.1f}% • {total_text}"


def _set_support_cards_visible(self, visible: bool) -> None:
    for name in ("buff_card", "debuff_card", "raid_debuff_card"):
        card = getattr(self, name, None)
        if card is not None:
            card.setVisible(visible)


def _build_kpi_card_with_crit(self):
    assert _ORIGINAL_BUILD_KPI_CARD is not None
    card = _ORIGINAL_BUILD_KPI_CARD(self)

    from widgets.performance_dashboard import _StatBlock

    self.kpi_crit = _StatBlock("Crit Rate")
    first = card.body_layout.itemAt(0)
    row = first.layout() if first is not None else None
    if row is not None:
        row.addWidget(self.kpi_crit, 1)
    else:
        card.addWidget(self.kpi_crit)
    self.kpi_crit.setVisible(False)
    return card


def _show_snapshot_with_dd(self, snapshot):
    assert _ORIGINAL_SHOW_SNAPSHOT is not None
    _ORIGINAL_SHOW_SNAPSHOT(self, snapshot)

    is_dd = str(getattr(snapshot, "Role", "")).casefold() == "dps"
    _set_support_cards_visible(self, not is_dd)

    crit = getattr(snapshot, "CritRatePercent", None)
    self.kpi_crit.setVisible(is_dd)
    if is_dd:
        if crit is None:
            self.kpi_crit.set_value("Unavailable")
        else:
            hits = int(getattr(snapshot, "DamageHitEvents", 0) or 0)
            critical = int(getattr(snapshot, "CriticalDamageEvents", 0) or 0)
            self.kpi_crit.set_value(f"{crit:.1f}% ({critical:,}/{hits:,})")

        self.abilities_card.title_label.setText(
            "Top Damage Abilities • contribution to total"
        )

        note = str(getattr(snapshot, "DdAnalysisNote", "") or "").strip()
        if note:
            self.kpi_crit.setToolTip(note)
        else:
            self.kpi_crit.setToolTip(
                "Critical damage events divided by all qualifying damage events in this fight."
            )


def _update_abilities_with_contribution(self, abilities, color: str):
    layout = self.abilities_list_layout

    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()

    if not abilities:
        from PySide6.QtWidgets import QLabel

        placeholder = QLabel("No ability data yet")
        placeholder.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(placeholder)
        return

    from widgets.performance_dashboard import _AbilityRow

    max_total = max((a.Total for a in abilities), default=0.0) or 1.0
    for ability in abilities:
        bar_percent = (ability.Total / max_total) * 100.0
        layout.addWidget(
            _AbilityRow(
                name=ability.Name,
                icon_slug=ability.IconSlug,
                value_text=_ability_value_text(ability.Percent, ability.Total),
                percent=bar_percent,
                color=color,
            )
        )


def install() -> None:
    global _INSTALLED, _ORIGINAL_BUILD_KPI_CARD, _ORIGINAL_SHOW_SNAPSHOT
    global _ORIGINAL_UPDATE_ABILITIES
    if _INSTALLED:
        return

    from widgets.performance_dashboard import PerformanceDashboard

    _ORIGINAL_BUILD_KPI_CARD = PerformanceDashboard._build_kpi_card
    _ORIGINAL_SHOW_SNAPSHOT = PerformanceDashboard.show_snapshot
    _ORIGINAL_UPDATE_ABILITIES = PerformanceDashboard._update_abilities_list

    PerformanceDashboard._build_kpi_card = _build_kpi_card_with_crit
    PerformanceDashboard.show_snapshot = _show_snapshot_with_dd
    PerformanceDashboard._update_abilities_list = _update_abilities_with_contribution
    _INSTALLED = True

    from ui.performance_dashboard_dd_dot_support import install as install_dot_ui
    from ui.performance_dashboard_dd_weave_support import install as install_weave_ui
    from ui.performance_dashboard_role_surface_support import install as install_role_surface

    install_dot_ui()
    install_weave_ui()
    install_role_surface()

    # app.py installs DD dashboard support last among MainWindow-affecting startup
    # layers. Use that stable bootstrap point so deferred pages wrap the completed
    # UI stack rather than forcing another broad startup rewrite.
    from ui.main_window_lazy_page_support import install as install_lazy_pages

    install_lazy_pages()
