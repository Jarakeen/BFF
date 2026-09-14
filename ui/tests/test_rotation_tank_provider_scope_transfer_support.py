from pathlib import Path
from types import SimpleNamespace

import ui.rotation_tank_provider_scope_transfer_support as support_module
from ui.rotation_tank_provider_scope_transfer_support import (
    refresh_rotation_tank_provider_scope,
)


class _RotationPage:
    def __init__(self, build, encounter_id="taleria_hm"):
        self.build = build
        self.encounter_id = encounter_id
        self.received = None

    def _selected_build(self):
        return self.build

    def _selected_encounter_id(self):
        return self.encounter_id

    def set_rotation_generate_tank_assignment_evidence(self, rows):
        self.received = tuple(rows)


class _ProviderScopeService:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


def _tank():
    return SimpleNamespace(Name="Tank A", BuildName="MT", Role="Tank")


def _assignment(build, slot_name):
    return SimpleNamespace(
        slot_name=slot_name,
        player_name=build.Name,
        source_build_name=build.BuildName,
    )


def _optimization_page(*builds, assignments=None):
    rows = (
        tuple(assignments)
        if assignments is not None
        else tuple(
            _assignment(build, f"Slot {index}")
            for index, build in enumerate(builds, start=1)
        )
    )
    return SimpleNamespace(
        roster=SimpleNamespace(Members=list(builds)),
        current_prescription=SimpleNamespace(assignments=rows),
    )


def _window(rotation_page, optimization_page=None):
    return SimpleNamespace(
        pages={
            "rotations": rotation_page,
            "console:6": optimization_page or SimpleNamespace(),
        }
    )


def test_transfer_delivers_provider_scope_and_symbolic_policy_to_rotation():
    tank = _tank()
    teammate = SimpleNamespace(Name="Healer A", BuildName="Heal", Role="Healer")
    rotation_page = _RotationPage(tank)
    window = _window(rotation_page, _optimization_page(tank, teammate))
    policy_resolution = SimpleNamespace(
        taunt_policies=("apply",),
        taunt_maintenance_policies=("maintain",),
    )
    service = _ProviderScopeService(
        SimpleNamespace(
            encounter_id="taleria_hm",
            member_id="tank-a",
            assignments=("assignment",),
            policy_resolution=policy_resolution,
            taunt_maintenance_horizon_policies=("until-end",),
            unresolved=("symbolic horizon awaits Generate",),
        )
    )

    result = refresh_rotation_tank_provider_scope(
        window,
        provider_scope_service=service,
    )

    assert result.transferred is True
    assert result.member_id == "tank-a"
    assert result.unresolved == ("symbolic horizon awaits Generate",)
    assert len(rotation_page.received) == 1
    evidence = rotation_page.received[0]
    assert evidence.encounter_id == "taleria_hm"
    assert evidence.member_id == "tank-a"
    assert evidence.assignments == ("assignment",)
    assert evidence.taunt_policies == ("apply",)
    assert evidence.taunt_maintenance_policies == ("maintain",)
    assert evidence.taunt_maintenance_horizon_policies == ("until-end",)
    assert service.calls[0]["roster_builds"] == (tank, teammate)


def test_transfer_uses_authoritative_prescription_without_team_table():
    tank = _tank()
    teammate = SimpleNamespace(Name="Healer A", BuildName="Heal", Role="Healer")
    rotation_page = _RotationPage(tank)
    optimization_page = _optimization_page(tank, teammate)
    assert not hasattr(optimization_page, "team_table")
    window = _window(rotation_page, optimization_page)
    service = _ProviderScopeService(
        SimpleNamespace(
            encounter_id="taleria_hm",
            member_id="tank-a",
            assignments=(),
            policy_resolution=SimpleNamespace(
                taunt_policies=(), taunt_maintenance_policies=()
            ),
            taunt_maintenance_horizon_policies=(),
            unresolved=(),
        )
    )

    result = refresh_rotation_tank_provider_scope(
        window,
        provider_scope_service=service,
    )

    assert result.transferred is True
    assert service.calls[0]["roster_builds"] == (tank, teammate)


def test_non_tank_rotation_selection_clears_stale_tank_evidence():
    rotation_page = _RotationPage(
        SimpleNamespace(Name="DD A", BuildName="Parse", Role="Damage Dealer")
    )
    rotation_page.received = ("stale",)
    window = _window(rotation_page)

    result = refresh_rotation_tank_provider_scope(window, provider_scope_service=object())

    assert result.transferred is False
    assert result.unresolved == ()
    assert rotation_page.received == ()


def test_missing_authoritative_prescription_fails_closed_and_clears_evidence():
    tank = _tank()
    rotation_page = _RotationPage(tank)
    rotation_page.received = ("stale",)
    optimization_page = SimpleNamespace(
        roster=SimpleNamespace(Members=[tank]),
        current_prescription=None,
    )
    window = _window(rotation_page, optimization_page)

    result = refresh_rotation_tank_provider_scope(window, provider_scope_service=object())

    assert result.transferred is False
    assert "no authoritative current prescription" in result.unresolved[0]
    assert rotation_page.received == ()


def test_open_prescription_chair_fails_closed_and_clears_evidence():
    tank = _tank()
    rotation_page = _RotationPage(tank)
    rotation_page.received = ("stale",)
    open_chair = SimpleNamespace(
        slot_name="Off Tank",
        player_name=None,
        source_build_name=None,
    )
    optimization_page = _optimization_page(
        tank,
        assignments=(_assignment(tank, "Main Tank"), open_chair),
    )
    window = _window(rotation_page, optimization_page)

    result = refresh_rotation_tank_provider_scope(window, provider_scope_service=object())

    assert result.transferred is False
    assert result.unresolved == (
        "Off Tank: prescription does not identify an exact saved player",
    )
    assert rotation_page.received == ()


def test_provider_scope_resolution_failure_does_not_leave_stale_evidence():
    tank = _tank()
    rotation_page = _RotationPage(tank)
    rotation_page.received = ("stale",)
    window = _window(rotation_page, _optimization_page(tank))
    service = _ProviderScopeService(error=ValueError("selected Tank is not on selected team"))

    result = refresh_rotation_tank_provider_scope(
        window,
        provider_scope_service=service,
    )

    assert result.transferred is False
    assert result.unresolved == ("selected Tank is not on selected team",)
    assert rotation_page.received == ()


def test_generate_refreshes_provider_scope_before_canonical_generation(monkeypatch):
    calls = []
    owner = object()
    page = SimpleNamespace(_rotation_tank_provider_scope_transfer_owner=owner)

    monkeypatch.setattr(
        support_module,
        "refresh_rotation_tank_provider_scope",
        lambda window: calls.append(("refresh", window)),
    )
    monkeypatch.setattr(
        support_module,
        "_ORIGINAL_GENERATE",
        lambda _self, generated_page: calls.append(("generate", generated_page)),
    )

    support_module._generate_with_fresh_tank_provider_scope(object(), page)

    assert calls == [("refresh", owner), ("generate", page)]


def test_transfer_support_is_installed_before_main_window_construction():
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    assert "install_rotation_tank_provider_scope_transfer_support()" in installer
