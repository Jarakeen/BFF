from pathlib import Path


def test_phase14_optimization_constructor_skips_legacy_initialization() -> None:
    source = Path("ui/team_optimization_phase14_shell_support.py").read_text(
        encoding="utf-8"
    )
    init = source.split("def _init_with_phase14_workbench", 1)[1].split(
        "def _ensure_adviser_services", 1
    )[0]

    assert "FoundryPage.__init__(self, parent)" in init
    assert "_ORIGINAL_INIT(self, parent)" not in init
    assert "BuildService(" not in init
    assert "SavedBuildCapabilityService(" not in init
    assert '"legacy_constructor_invoked": False' in init
    assert '"build_resolution_deferred": True' in init
    assert '"adviser_service_deferred": True' in init


def test_phase14_optimization_lazily_creates_plan_scoped_services() -> None:
    source = Path("ui/team_optimization_phase14_shell_support.py").read_text(
        encoding="utf-8"
    )
    lazy = source.split("def _ensure_adviser_services", 1)[1].split(
        "def _set_scope_with_phase14_workbench", 1
    )[0]
    scope = source.split("def _set_scope_with_phase14_workbench", 1)[1].split(
        "def install()", 1
    )[0]

    assert "BuildService(data_dir / \"builds.json\")" in lazy
    assert "SavedBuildCapabilityService(builds, data_dir / \"eso.db\")" in lazy
    assert "RaidPlanOptimizerAdviserService(capability)" in lazy
    assert "_ensure_adviser_services(self)" in scope
    assert "self._optimizer_saved_build_service.load()" in scope
    assert "total_chairs=len(_CANONICAL_SEATS)" in scope
    assert "_render_workbench(self, raid_plan, review)" in scope
    assert "_ORIGINAL_SET_SCOPE(self, raid_plan)" not in scope


def test_startup_does_not_install_legacy_optimization_construction_stack() -> None:
    bootstrap = Path("ui/application_team_optimization_bootstrap.py").read_text(
        encoding="utf-8"
    )
    dashboard = Path("ui/raid_engine_dashboard_support.py").read_text(
        encoding="utf-8"
    )

    assert "team_optimization_role_cleanup" not in bootstrap
    assert "install_role_cleanup()" not in bootstrap
    assert "team_optimization_canonical_analysis_support" not in bootstrap
    assert "install_team_optimization_canonical_analysis()" not in bootstrap
    assert "raid_plan_optimizer_adviser_support" not in dashboard
    assert "install_raid_plan_optimizer_adviser_support()" not in dashboard
    assert "install_team_optimization_phase14_shell_support()" in dashboard


def test_legacy_provider_workload_does_not_rewrap_optimization_after_shell() -> None:
    source = Path("ui/team_provider_workload_support.py").read_text(
        encoding="utf-8"
    )
    install = source.split("def install() -> None:", 1)[1]

    assert "OptimizationPage.__init__ =" not in install
    assert "OptimizationPage._update_team_analysis =" not in install
    assert "OptimizationPage.set_provider_workload_evidence" not in install
    assert "CompBuilderPage.set_provider_workload_evidence" in install


def test_main_window_keeps_console_6_but_not_legacy_optimizer_send_control() -> None:
    source = Path("ui/main_window.py").read_text(encoding="utf-8")

    assert '"console:6": optimization_page' in source
    construction = source.split("optimization_page = OptimizationPage()", 1)[1].split(
        "core_pages = {", 1
    )[0]
    assert "Send Team to Raid Plan" not in construction
    assert "_send_optimized_team_to_roster" not in construction


def test_startup_profiler_reports_constructor_and_optional_plan_scope() -> None:
    source = Path("tools/profile_team_optimization_startup.py").read_text(
        encoding="utf-8"
    )

    assert "construction_ms_median" in source
    assert "plan_scope_ms_median" in source
    assert "legacy_constructor_invoked=False" in source
    assert "saved_build_resolution_at_startup=False" in source
    assert "page.set_raid_plan_adviser_scope(plan)" in source
