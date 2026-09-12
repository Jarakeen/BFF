from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QTableWidget, QTableWidgetItem

from models.build_model import BuildRoster, PlayerBuild
from services.performance_raid_review_selection_mode_service import PerformanceRaidReviewSelectionModeService
from ui.coverage_page import CoveragePage
from ui.foundry_page import FoundryPage
from ui.raid_engine_dashboard_page import RaidEngineDashboardPage


def test_selected_optimization_team_reaches_coverage_without_importing_other_builds(tmp_path, monkeypatch):
    from ui import coverage_page

    QApplication.instance() or QApplication([])
    database = tmp_path / "eso.db"
    database.touch()
    monkeypatch.setattr(coverage_page, "DEFAULT_DATABASE", database)

    susan = PlayerBuild(Name="Susan", BuildName="Necro Tank")
    magrat = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    roster = BuildRoster(Members=[susan, magrat])
    audit_calls = []

    def audit(build):
        audit_calls.append(build.Name)
        effect = "major_courage" if build.Name == "Susan" else "major_slayer"
        return SimpleNamespace(
            resolved_effects=(SimpleNamespace(name=effect, condition=None, trigger=None),),
            capability_unresolved=(),
        )

    coverage = CoveragePage.__new__(CoveragePage)
    FoundryPage.__init__(coverage)
    coverage.build_service = SimpleNamespace(load=lambda: roster, save=lambda _: (_ for _ in ()).throw(AssertionError("read only")))
    coverage.capability_service = SimpleNamespace(audit_build=audit)
    coverage.raid_review_runner = SimpleNamespace(available_encounters=lambda: ())
    coverage.raid_review_selection_mode_service = PerformanceRaidReviewSelectionModeService()
    coverage._raid_review_task = None
    coverage._team_scope = ()
    coverage._team_scope_name = ""
    coverage._team_total_slots = 12
    coverage._build_ui()
    coverage.refresh()
    assert coverage.table.item(0, 3).text() == "Susan"

    table = QTableWidget(2, 2)
    table.setItem(0, 0, QTableWidgetItem("Main Tank"))
    first = QComboBox()
    first.addItem("Open", None)
    first.addItem("Susan — Necro Tank", 0)
    first.setCurrentIndex(1)
    table.setCellWidget(0, 1, first)
    table.setItem(1, 0, QTableWidgetItem("Off Tank"))
    second = QComboBox()
    second.addItem("Open", None)
    table.setCellWidget(1, 1, second)
    optimization = SimpleNamespace(team_table=table, roster=roster, refresh=lambda: None)
    dashboard = RaidEngineDashboardPage()
    dashboard.set_sources(optimization=optimization, coverage=coverage)

    snapshot = dashboard._coverage_snapshot()
    assert dict(snapshot.effects)["Major Courage"] == "available"
    assert dict(snapshot.effects)["Major Slayer"] == "not_found"
    assert snapshot.covered == 1 and snapshot.total == 15
    assert dashboard.send_coverage_button.isEnabled()
    assert "Missing" not in " ".join(label.text() for label in dashboard.coverage_card.findChildren(QLabel))

    destinations = []
    dashboard.pageRequested.connect(destinations.append)
    dashboard._send_team_to_coverage()
    assert destinations == ["console:7"]
    assert coverage.scope_combo.currentData() == "team"
    assert "1/12 slots with saved builds" in coverage.scope_note.text()
    assert "Main Tank: Susan" in coverage.scope_note.text()
    assert coverage.table.item(4, 8).text() == "Not identified"  # Major Slayer
    assert "Magrat" not in coverage.scope_note.text()

    dashboard._browse_all_coverage()
    assert coverage.scope_combo.currentData() == "all"
    assert coverage.table.item(4, 3).text() == "Magrat"
    assert audit_calls and all(name in {"Susan", "Magrat"} for name in audit_calls)
