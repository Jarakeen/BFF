from types import SimpleNamespace

from ui.performance_dashboard_role_surface_support import (
    _apply_role_name_surface,
    _apply_role_surface,
    _canonical_performance_role,
    _sync_actor_role_picker,
)


class _Card:
    def __init__(self):
        self.visible = None

    def setVisible(self, visible: bool) -> None:
        self.visible = bool(visible)


class _Picker:
    def __init__(self, text: str = "Healer"):
        self.text = text
        self.index = 0

    def currentText(self) -> str:
        return self.text

    def setCurrentText(self, text: str) -> None:
        self.text = text
        self.index = 0

    def setCurrentIndex(self, index: int) -> None:
        self.index = index
        if index < 0:
            self.text = ""


def _page():
    names = (
        "support_effects_card",
        "graph_effect_card",
        "_performance_tracking_card",
        "kpi_card",
        "dot_card",
        "dd_readout_card",
        "output_card",
        "abilities_card",
        "quick_read_card",
        "buff_card",
        "debuff_card",
        "raid_debuff_card",
    )
    return SimpleNamespace(**{name: _Card() for name in names})


def test_dps_surface_hides_generic_support_and_shows_dd_diagnostics() -> None:
    page = _page()

    _apply_role_surface(page, SimpleNamespace(Role="DPS"))

    assert page.support_effects_card.visible is False
    assert page.graph_effect_card.visible is True
    assert page._performance_tracking_card.visible is False
    assert page.buff_card.visible is False
    assert page.debuff_card.visible is False
    assert page.raid_debuff_card.visible is False

    assert page.kpi_card.visible is True
    assert page.dot_card.visible is True
    assert page.dd_readout_card.visible is True
    assert page.output_card.visible is True
    assert page.abilities_card.visible is True
    assert page.quick_read_card.visible is True


def test_healer_surface_restores_support_surface() -> None:
    page = _page()

    _apply_role_surface(page, SimpleNamespace(Role="Healer"))

    assert page.support_effects_card.visible is True
    assert page.graph_effect_card.visible is True
    assert page._performance_tracking_card.visible is True


def test_fresh_dps_member_keeps_graph_controls_without_showing_blank_results() -> None:
    page = _page()

    _apply_role_name_surface(page, "DPS", has_snapshot=False)

    assert page.support_effects_card.visible is False
    assert page.graph_effect_card.visible is True
    assert page._performance_tracking_card.visible is False
    assert page.buff_card.visible is False
    assert page.debuff_card.visible is False
    assert page.raid_debuff_card.visible is False

    # Initial empty-state plumbing still owns result visibility until a fight is shown.
    assert page.kpi_card.visible is None
    assert page.dot_card.visible is None
    assert page.dd_readout_card.visible is None
    assert page.output_card.visible is None
    assert page.abilities_card.visible is None
    assert page.quick_read_card.visible is None


def test_role_picker_can_restore_support_surface_before_snapshot() -> None:
    page = _page()

    _apply_role_name_surface(page, "DPS", has_snapshot=False)
    _apply_role_name_surface(page, "Healer", has_snapshot=False)

    assert page.support_effects_card.visible is True
    assert page.graph_effect_card.visible is True
    assert page._performance_tracking_card.visible is True


def test_common_damage_role_aliases_canonicalize_to_dps() -> None:
    for role in ("DPS", "dps", "DD", "damage", "Damage Dealer", "damage-dealer"):
        assert _canonical_performance_role(role) == "DPS"


def test_loaded_dps_actor_replaces_stale_healer_picker() -> None:
    picker = _Picker("Healer")
    actor = SimpleNamespace(Role="Damage Dealer")
    page = SimpleNamespace(
        role_override=picker,
        selected_actor=lambda: actor,
    )

    resolved = _sync_actor_role_picker(page)

    assert resolved == "DPS"
    assert picker.currentText() == "DPS"


def test_unknown_loaded_actor_role_clears_stale_healer_picker() -> None:
    picker = _Picker("Healer")
    actor = SimpleNamespace(Role="mystery-role")
    page = SimpleNamespace(
        role_override=picker,
        selected_actor=lambda: actor,
    )

    resolved = _sync_actor_role_picker(page)

    assert resolved is None
    assert picker.currentText() == ""
    assert picker.index == -1


def test_unknown_role_surface_does_not_fall_back_to_support_mode() -> None:
    page = _page()

    _apply_role_name_surface(page, "mystery-role", has_snapshot=False)

    assert page.support_effects_card.visible is False
    assert page._performance_tracking_card.visible is False
    assert page.graph_effect_card.visible is True
