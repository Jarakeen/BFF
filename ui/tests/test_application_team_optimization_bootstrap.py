from pathlib import Path


def test_hybrid_anchor_feature_no_longer_owns_application_composition() -> None:
    source = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    assert "install_role_cleanup()" not in source
    assert "install_comp_builder_workspace()" not in source
    assert "install_team_provider_workload_support()" not in source
    assert "install_rotation_tank_provider_scope_transfer_support()" not in source


def test_application_startup_owns_team_optimization_composition() -> None:
    source = Path("app.py").read_text(encoding="utf-8")

    assert (
        "from ui.application_team_optimization_bootstrap "
        "import bootstrap_team_optimization_extensions"
    ) in source
    assert source.index("install_team_optimization_hybrid_anchor_support()") < source.index(
        "bootstrap_team_optimization_extensions()"
    )
    assert source.index("bootstrap_team_optimization_extensions()") < source.index(
        "install_extreme_optimization_support()"
    )


def test_team_optimization_bootstrap_preserves_phase14_extension_order() -> None:
    source = Path("ui/application_team_optimization_bootstrap.py").read_text(
        encoding="utf-8"
    )

    assert "def bootstrap_team_optimization_extensions()" in source
    assert "install_role_cleanup()" not in source
    assert "install_team_optimization_canonical_analysis()" not in source
    assert "team_optimization_role_cleanup" not in source
    assert "team_optimization_canonical_analysis_support" not in source
    assert source.index("install_comp_builder_build_candidates()") < source.index(
        "install_comp_builder_candidate_picker()"
    )
    assert source.index("install_comp_builder_layout()") < source.index(
        "install_comp_builder_polish()"
    )
    assert source.index("install_team_provider_workload_support()") < source.index(
        "install_team_provider_saved_rotation_support()"
    )


def test_ordering_tests_no_longer_treat_hybrid_feature_as_bootstrap() -> None:
    legacy = "team_optimization_hybrid_anchor_support.py"
    offenders = []
    for root in (Path("services/tests"), Path("ui/tests")):
        for path in root.glob("test_*.py"):
            if path.name == Path(__file__).name:
                continue
            if legacy in path.read_text(encoding="utf-8"):
                offenders.append(path.as_posix())

    assert offenders == []
