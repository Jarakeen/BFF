from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ui.performance_dashboard_dd_support import (
    _ability_value_text,
    _set_support_cards_visible,
)


class _Card:
    def __init__(self):
        self.visible = None

    def setVisible(self, value: bool) -> None:
        self.visible = bool(value)


def test_ability_value_text_shows_contribution_and_compact_total() -> None:
    assert _ability_value_text(23.4, 4_250_000) == "23.4% • 4.25m"
    assert _ability_value_text(8.1, 725_000) == "8.1% • 725.0k"


def test_dd_support_adds_crit_kpi_and_contribution_title() -> None:
    source = Path("ui/performance_dashboard_dd_support.py").read_text(encoding="utf-8")
    assert '_StatBlock("Crit Rate")' in source
    assert '"Top Damage Abilities • contribution to total"' in source
    assert "CriticalDamageEvents" in source
    assert "DamageHitEvents" in source


def test_dd_support_can_hide_and_restore_support_uptime_cards() -> None:
    dashboard = SimpleNamespace(
        buff_card=_Card(),
        debuff_card=_Card(),
        raid_debuff_card=_Card(),
    )

    _set_support_cards_visible(dashboard, False)
    assert dashboard.buff_card.visible is False
    assert dashboard.debuff_card.visible is False
    assert dashboard.raid_debuff_card.visible is False

    _set_support_cards_visible(dashboard, True)
    assert dashboard.buff_card.visible is True
    assert dashboard.debuff_card.visible is True
    assert dashboard.raid_debuff_card.visible is True


def test_dd_support_is_installed_before_main_window_construction() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    assert "install_performance_dd_analysis_support()" in source
    assert "install_performance_dashboard_dd_support()" in source
    assert source.index("install_performance_dd_analysis_support()") < source.index(
        "from ui.main_window import MainWindow"
    )
