from __future__ import annotations

import sys
from types import SimpleNamespace

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.team_provider_workload_candidate_service import (
    TeamProviderWorkloadCandidateRejection,
    TeamProviderWorkloadCandidateResult,
)
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

    class _DataDir:
        def __truediv__(self, _name):
            return _name

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


def test_unspecified_rotation_plans_auto_load_saved_team_plans(monkeypatch):
    selected = object()
    saved = (_plan("Magrat", "DF Healer"),)
    captured = {}

    def _original(page, **kwargs):
        captured.update(kwargs)
        return "result"

    support._ORIGINAL_COMP_GENERATE = _original
    monkeypatch.setattr(support, "_saved_rotation_plans", lambda builds: saved if builds == (selected,) else ())
    monkeypatch.setitem(
        sys.modules,
        "ui.team_provider_workload_support",
        SimpleNamespace(_comp_selected_saved_builds=lambda page: (selected,)),
    )

    result = support._comp_generate_with_saved_rotations(
        object(),
        rotation_plans=None,
        progression_by_identity={},
        alternatives=(),
        policy=None,
    )

    assert result == "result"
    assert captured["rotation_plans"] == saved


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


def test_assigned_provider_bridge_merges_adapter_blockers_into_shared_candidate_result(monkeypatch):
    selected = (object(),)
    saved = (_plan("Magrat", "DF Healer"),)
    adapter_rejection = TeamProviderWorkloadCandidateRejection(
        alternative_id="major_slayer_provider",
        effect_key="major_slayer",
        blockers=("provider assignment is unresolved_selection, not assigned",),
    )
    generated_rejection = TeamProviderWorkloadCandidateRejection(
        alternative_id="other",
        effect_key="minor_courage",
        blockers=("generated blocker",),
    )
    projection = SimpleNamespace(alternatives=(), rejected=(adapter_rejection,))

    class _Adapter:
        @classmethod
        def project(cls, **kwargs):
            assert kwargs["rotation_plans"] == saved
            return projection

    class _Page:
        def __init__(self):
            self.set_calls = []

        def generate_provider_workload_candidates(self, **kwargs):
            assert kwargs["rotation_plans"] == saved
            assert kwargs["alternatives"] == ()
            return TeamProviderWorkloadCandidateResult(
                projections=(),
                rejected=(generated_rejection,),
            )

        def set_provider_workload_candidates(self, result, *, policy=None):
            self.set_calls.append((result, policy))

    monkeypatch.setattr(support, "TeamProviderAssignmentWorkloadAdapterService", _Adapter)
    monkeypatch.setattr(support, "_saved_rotation_plans", lambda builds: saved if builds == selected else ())
    page = _Page()

    result = support._generate_assigned_provider_workload_candidates(
        page,
        selected_builds=selected,
        assignments=(),
        effect_policies=(),
        workload_policies=(),
        progression_by_identity={},
        rotation_plans=None,
        policy="raid policy",
    )

    assert result.rejected == (adapter_rejection, generated_rejection)
    assert page.set_calls == [(result, "raid policy")]


def test_saved_rotation_installer_targets_comp_only_not_phase14_optimization() -> None:
    from pathlib import Path

    source = Path("ui/team_provider_saved_rotation_support.py").read_text(
        encoding="utf-8"
    )
    install = source.split("def install() -> None:", 1)[1]

    assert "from ui.optimization_page import OptimizationPage" not in install
    assert "OptimizationPage.generate_provider_workload_candidates" not in install
    assert "OptimizationPage.generate_assigned_provider_workload_candidates" not in install
    assert "CompBuilderPage.generate_provider_workload_candidates" in install
    assert "CompBuilderPage.generate_assigned_provider_workload_candidates" in install


def test_installer_orders_saved_rotation_bridge_after_workload_support():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "application_team_optimization_bootstrap.py"
    ).read_text(encoding="utf-8")

    workload = source.index("install_team_provider_workload_support()")
    saved = source.index("install_team_provider_saved_rotation_support()")
    assert workload < saved
