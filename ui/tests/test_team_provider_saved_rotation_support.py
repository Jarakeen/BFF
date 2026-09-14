from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
import ui.team_provider_saved_rotation_support as support


def _plan(character="Old Magrat", build="Old Healer"):
    return RotationPlan(
        character,
        build,
        30.0,
        (
            RotationAction(
                0.0,
                0,
                RotationActionKind.SKILL,
                "Combat Prayer",
                "front",
            ),
        ),
        assumptions=("saved exact plan",),
        unresolved=("saved unresolved evidence",),
    )


def test_saved_rotation_loader_uses_canonical_build_id_and_rebinds_display_identity(monkeypatch):
    selected = SimpleNamespace(
        Gamertag="Jarakeen",
        Name="Magrat",
        BuildName="DF Healer",
    )
    catalog = object()

    class _BuildService:
        def __init__(self, _path):
            self.canonical = SimpleNamespace(catalog_service=catalog)

    class _Artifacts:
        def __init__(self, _path):
            pass

        def get_rotation_plan(self, build_id):
            assert build_id == "canonical-magrat-df"
            return _plan()

    monkeypatch.setattr(support, "BuildService", _BuildService)
    monkeypatch.setattr(support, "BuildRotationArtifactService", _Artifacts)
    monkeypatch.setattr(
        support,
        "resolve_canonical_build_id",
        lambda actual_catalog, build: (
            "canonical-magrat-df"
            if actual_catalog is catalog and build is selected
            else None
        ),
    )
    monkeypatch.setattr(support, "get_data_dir", lambda: SimpleNamespace(__truediv__=None))

    # Path composition only needs an object supporting `/`; avoid touching disk.
    class _DataDir:
        def __truediv__(self, _name):
            return _name

    monkeypatch.setattr(support, "get_data_dir", lambda: _DataDir())

    plans = support._saved_rotation_plans((selected,))

    assert len(plans) == 1
    restored = plans[0]
    assert restored.character_name == "Magrat"
    assert restored.build_name == "DF Healer"
    assert restored.actions == _plan().actions
    assert restored.assumptions == ("saved exact plan",)
    assert restored.unresolved == ("saved unresolved evidence",)


def test_saved_rotation_loader_ignores_selected_build_without_saved_artifact(monkeypatch):
    selected = SimpleNamespace(Gamertag="Jarakeen", Name="Magrat", BuildName="DF Healer")

    class _BuildService:
        def __init__(self, _path):
            self.canonical = SimpleNamespace(catalog_service=object())

    class _Artifacts:
        def __init__(self, _path):
            pass

        def get_rotation_plan(self, _build_id):
            return None

    class _DataDir:
        def __truediv__(self, _name):
            return _name

    monkeypatch.setattr(support, "BuildService", _BuildService)
    monkeypatch.setattr(support, "BuildRotationArtifactService", _Artifacts)
    monkeypatch.setattr(support, "resolve_canonical_build_id", lambda _catalog, _build: "id")
    monkeypatch.setattr(support, "get_data_dir", lambda: _DataDir())

    assert support._saved_rotation_plans((selected,)) == ()


def test_explicit_rotation_plans_bypass_saved_plan_discovery(monkeypatch):
    captured = {}

    def _original(page, **kwargs):
        captured.update(kwargs)
        return "result"

    support._ORIGINAL_COMP_GENERATE = _original
    monkeypatch.setattr(
        support,
        "_saved_rotation_plans",
        lambda _builds: (_ for _ in ()).throw(AssertionError("must not auto-load")),
    )

    result = support._comp_generate_with_saved_rotations(
        object(),
        rotation_plans=(),
        progression_by_identity={},
        alternatives=(),
        policy=None,
    )

    assert result == "result"
    assert captured["rotation_plans"] == ()


def test_installer_orders_saved_rotation_bridge_after_workload_support():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "team_optimization_hybrid_anchor_support.py"
    ).read_text(encoding="utf-8")

    workload = source.index("install_team_provider_workload_support()")
    saved = source.index("install_team_provider_saved_rotation_support()")
    assert workload < saved
