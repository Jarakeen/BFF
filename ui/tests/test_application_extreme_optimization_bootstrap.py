from pathlib import Path


def test_extreme_page_feature_no_longer_owns_extension_composition() -> None:
    support_source = Path("ui/extreme_optimization_support.py").read_text(encoding="utf-8")
    page_source = Path("ui/extreme_optimization_page.py").read_text(encoding="utf-8")

    assert "install_extreme_critical_profile_support()" not in support_source
    assert "install_extreme_blueprint_result_support()" not in support_source
    assert "install_extreme_max_health_record_support()" not in support_source
    assert "install_extreme_stamina_recovery_record_support()" not in support_source

    # Saved-build execution is now owned directly by the page and the canonical
    # execution catalog.  The installer only supplies the completed blueprint
    # layer while registering the page.
    assert "self.service = ExtremeCompleteOptimizationService()" in page_source
    assert "self.execution_rows = ExtremeRecordExecutionCatalogService.descriptors()" in page_source
    assert "page.service = ExtremeCompleteOptimizationService()" not in support_source
    assert "page.blueprint_service = ExtremeCompleteBlueprintService()" in support_source


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
