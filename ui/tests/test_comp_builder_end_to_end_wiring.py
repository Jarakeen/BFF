from pathlib import Path


def test_comp_builder_navigation_and_page_registry_are_same_route() -> None:
    sidebar = Path("ui/components/foundry_sidebar.py").read_text(encoding="utf-8")
    main = Path("ui/main_window.py").read_text(encoding="utf-8")

    assert '("Comp Builder", "comp_builder")' in sidebar
    assert 'from ui.comp_builder_page import CompBuilderPage' in main
    assert '"comp_builder": comp_builder_page' in main
    assert 'comp_builder_page = CompBuilderPage()' in main


def test_comp_builder_bootstraps_before_main_window_construction() -> None:
    app = Path("app.py").read_text(encoding="utf-8")

    workspace = app.index("bootstrap_workspace_extensions()")
    team = app.index("bootstrap_team_optimization_extensions()")
    import_main = app.index("from ui.main_window import MainWindow")
    construct = app.index("window = MainWindow()")

    assert workspace < team < import_main < construct


def test_roster_to_comp_builder_bridge_is_installed_after_roster_action_surface() -> None:
    workspace = Path("ui/application_workspace_bootstrap.py").read_text(encoding="utf-8")
    intake = Path("ui/comp_builder_roster_intake_support.py").read_text(encoding="utf-8")
    roster_actions = Path("ui/roster_assignment_action_support.py").read_text(encoding="utf-8")

    assert workspace.index("install_roster_assignment_action_support()") < workspace.index(
        "install_comp_builder_roster_intake_support()"
    )
    assert 'send.clicked.connect(lambda *_: _send_to_comp_maker(page))' in roster_actions
    assert 'assignment_actions._send_to_comp_maker = _send_roster_team_to_comp' in intake
    assert 'assignment_actions._show_page(page, "comp_builder")' in intake
    assert "comp.apply_roster_team_context(" in intake


def test_comp_builder_return_to_roster_is_connected_through_signal() -> None:
    main = Path("ui/main_window.py").read_text(encoding="utf-8")
    candidates = Path("ui/comp_builder_build_candidate_support.py").read_text(encoding="utf-8")

    assert "comp_builder_page.rosterPlanSent.connect(self._show_generated_roster_plan)" in main
    assert 'self.show_page("roster_page")' in main
    assert "self.rosterPlanSent.emit(plan.name)" in candidates


def test_option_two_visible_layers_are_installed_in_final_comp_builder_stack() -> None:
    bootstrap = Path("ui/application_team_optimization_bootstrap.py").read_text(encoding="utf-8")
    layout = Path("ui/comp_builder_layout_support.py").read_text(encoding="utf-8")
    polish = Path("ui/comp_builder_polish_support.py").read_text(encoding="utf-8")
    workspace = Path("ui/comp_builder_workspace_support.py").read_text(encoding="utf-8")

    assert "install_comp_builder_workspace()" in bootstrap
    assert "install_comp_builder_main_controls()" in bootstrap
    assert "install_comp_builder_layout()" in bootstrap
    assert "install_comp_builder_polish()" in bootstrap
    assert bootstrap.index("install_comp_builder_layout()") < bootstrap.index(
        "install_comp_builder_polish()"
    )

    assert 'matrix.title_label.setText("Team")' in layout
    assert 'coverage.title_label.setText("Team Health")' in layout
    assert 'details.title_label.setText("Selected Player / Build Recommendation")' in layout
    assert 'details.set_title("Selected Player / Build Recommendation")' in polish
    assert 'QPushButton("Advanced Assignment Details ▸")' in workspace
    assert "editor_host.setVisible(False)" in workspace
