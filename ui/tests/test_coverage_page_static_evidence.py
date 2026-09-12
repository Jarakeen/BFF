from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox

from models.build_model import BuildRoster, PlayerBuild
from services.raid_coverage_profile import DEFAULT_RAID_COVERAGE_PROFILE
from services.saved_build_capability_service import summarize_raid_coverage
from ui.coverage_page import CoveragePage
from ui.foundry_page import FoundryPage


def _audit(*effects, unresolved=()):
    return SimpleNamespace(resolved_effects=effects, capability_unresolved=unresolved)


def _effect(name, condition=None):
    return SimpleNamespace(name=name, condition=condition, trigger=None)


def test_static_coverage_requires_canonical_effect_and_preserves_unknowns():
    build = PlayerBuild(Name="Magrat", FrontBarSkills=["War Horn", "Major Courage"])
    snapshot = summarize_raid_coverage(DEFAULT_RAID_COVERAGE_PROFILE, [
        (build, _audit(_effect("force"), _effect("major_slayer", "on ultimate use"), unresolved=("unknown skill",))),
    ])
    assert snapshot.status["War Horn"] == "unverified"
    assert snapshot.status["Major Courage"] == "unverified"
    assert snapshot.status["Major Slayer"] == "conditional"
    assert snapshot.conditional_providers["Major Slayer"] == ["Magrat"]
    assert snapshot.status["Minor Brittle"] == "unverified"


def test_coverage_page_filters_real_static_evidence_without_claiming_uptime(tmp_path, monkeypatch):
    from ui import coverage_page

    QApplication.instance() or QApplication([])
    database = tmp_path / "eso.db"
    database.touch()
    monkeypatch.setattr(coverage_page, "DEFAULT_DATABASE", database)
    page = CoveragePage.__new__(CoveragePage)
    FoundryPage.__init__(page)
    builds = BuildRoster(Members=[
        PlayerBuild(Name="Magrat", FrontBarSkills=["War Horn", "Major Courage"]),
        PlayerBuild(Name="Susan"),
    ])
    page.build_service = SimpleNamespace(load=lambda: builds)
    page.capability_service = SimpleNamespace(audit_build=lambda _build: _audit(
        _effect("major_courage"), _effect("minor_brittle", "requires frost"), _effect("force")
    ) if _build.Name == "Magrat" else _audit(_effect("major_courage")))
    page.status = SimpleNamespace(info=lambda *_: None, warning=lambda *_: None)
    page.scope_combo = QComboBox(page)
    page.scope_combo.addItem("All Saved Builds", "all")
    page._team_scope = ()
    workspace = page._coverage_tab()
    workspace.setParent(page)
    page.refresh()
    rows = {page.table.item(i, 0).text(): i for i in range(page.table.rowCount())}
    def state(name):
        return page.table.item(rows[name], 8).data(Qt.ItemDataRole.UserRole)

    assert state("Major Courage") == "available"
    assert page.table.item(rows["Major Courage"], 3).text() == "Magrat, Susan"
    assert page.table.item(rows["Major Courage"], 4).text() == "—"
    assert page.table.item(rows["Major Courage"], 7).text() == "—"
    assert state("Minor Brittle") == "conditional"
    assert state("War Horn") == "unverified"
    assert state("Major Slayer") == "not_found"
    assert not page.table.isRowHidden(rows["War Horn"])
    page.missing_only.setChecked(True)
    assert page.table.isRowHidden(rows["Major Courage"])
    assert not page.table.isRowHidden(rows["Minor Brittle"])
    page.missing_only.setChecked(False)
    page.redundant_only.setChecked(True)
    assert not page.table.isRowHidden(rows["Major Courage"])
    assert page.table.isRowHidden(rows["Minor Brittle"])
    page.redundant_only.setChecked(False)
    page.effect_filter.setCurrentText("Debuffs")
    assert not page.table.isRowHidden(rows["Minor Brittle"])
    assert page.table.isRowHidden(rows["Major Courage"])
    page.effect_filter.setCurrentText("All Effects")
    page.search.setText("Susan")
    assert not page.table.isRowHidden(rows["Major Courage"])
    assert page.table.isRowHidden(rows["War Horn"])
