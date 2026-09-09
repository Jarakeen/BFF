import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def test_shared_workload_card_is_installed_after_comp_maker_polish():
    source = (ROOT / "ui" / "team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    polish = source.index("install_comp_builder_polish()")
    workload = source.index("install_team_provider_workload_support()")
    assert polish < workload


def test_workload_support_targets_both_surfaces_and_invalidates_stale_results():
    source = (ROOT / "ui" / "team_provider_workload_support.py").read_text(
        encoding="utf-8"
    )

    assert 'FoundryCard("Provider Rotation Workload", "↻")' in source
    assert "CompBuilderPage.set_provider_workload_evidence" in source
    assert "OptimizationPage.set_provider_workload_evidence" in source
    assert "CompBuilderPage.generate_provider_workload_candidates" in source
    assert "OptimizationPage.generate_provider_workload_candidates" in source
    assert "_comp_selected_saved_builds(page)" in source
    assert "_optimization_selected_saved_builds(page)" in source
    assert "CompBuilderPage._refresh_coverage = _comp_refresh_with_provider_invalidation" in source
    assert (
        "OptimizationPage._update_team_analysis = "
        "_optimization_update_with_provider_invalidation"
    ) in source
    assert "setStyleSheet" not in source


def test_workload_card_starts_with_honest_boundary_and_rejects_wrong_evidence():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
    from ui.team_provider_workload_support import (
        _install_workload_card,
        _set_provider_workload_evidence,
    )

    app = QApplication.instance() or QApplication([])
    page = QWidget()
    page.workspace_layout = QVBoxLayout(page)

    _install_workload_card(page)

    assert page.provider_workload_card.property("providerWorkloadCard") is True
    assert "No canonical provider rotation workload" in page.provider_workload_text.text()
    with pytest.raises(TypeError, match="canonical workload results"):
        _set_provider_workload_evidence(page, (object(),))
    page.deleteLater()
    app.processEvents()
