from pathlib import Path


def test_extreme_page_feature_no_longer_owns_extension_composition() -> None:
    source = Path("ui/extreme_optimization_support.py").read_text(encoding="utf-8")

    assert "install_extreme_critical_profile_support()" not in source
    assert "install_extreme_blueprint_result_support()" not in source
    assert "install_extreme_max_health_record_support()" not in source
    assert "install_extreme_stamina_recovery_record_support()" not in source
    assert "page.service = ExtremeCompleteOptimizationService()" in source
    assert "page.blueprint_service = ExtremeCompleteBlueprintService()" in source


def test_application_startup_owns_extreme_extension_composition() -> None:
    source = Path("app.py").read_text(encoding="utf-8")

    assert (
        "from ui.application_extreme_optimization_bootstrap "
        "import bootstrap_extreme_optimization_extensions"
    ) in source
    assert source.index("bootstrap_team_optimization_extensions()") < source.index(
        "bootstrap_extreme_optimization_extensions()"
    )
    assert source.index("bootstrap_extreme_optimization_extensions()") < source.index(
        "install_extreme_optimization_support()"
    )


def test_extreme_bootstrap_preserves_extension_order() -> None:
    source = Path("ui/application_extreme_optimization_bootstrap.py").read_text(
        encoding="utf-8"
    )

    ordered_calls = (
        "install_extreme_critical_profile_support()",
        "install_extreme_class_configuration_support()",
        "install_extreme_blueprint_result_support()",
        "install_extreme_max_magicka_record_support()",
        "install_extreme_max_health_record_support()",
        "install_extreme_max_stamina_record_support()",
        "install_extreme_health_recovery_record_support()",
        "install_extreme_magicka_recovery_record_support()",
        "install_extreme_stamina_recovery_record_support()",
    )
    positions = [source.index(call) for call in ordered_calls]

    assert "def bootstrap_extreme_optimization_extensions()" in source
    assert positions == sorted(positions)
