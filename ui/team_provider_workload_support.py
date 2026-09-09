from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from services.team_provider_rotation_workload_service import (
    TeamProviderRotationWorkload,
    TeamProviderRotationWorkloadComparison,
)
from services.team_provider_workload_explanation_service import (
    TeamProviderWorkloadExplanationService,
)
from ui.components.foundry_card import FoundryCard


_INSTALLED = False
_ORIGINAL_COMP_INIT = None
_ORIGINAL_COMP_REFRESH = None
_ORIGINAL_OPTIMIZATION_INIT = None
_ORIGINAL_OPTIMIZATION_UPDATE = None


def _install_workload_card(page) -> None:
    page.provider_workload_card = FoundryCard("Provider Rotation Workload", "↻")
    page.provider_workload_card.setProperty("providerWorkloadCard", True)
    page.provider_workload_text = QLabel()
    page.provider_workload_text.setWordWrap(True)
    page.provider_workload_text.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
    )
    page.provider_workload_text.setProperty("providerWorkloadEvidence", True)
    page.provider_workload_card.addWidget(page.provider_workload_text)
    page.workspace_layout.addWidget(page.provider_workload_card)
    page._provider_rotation_workloads = ()
    page._provider_rotation_workload_comparison = None
    _render_provider_workload(page)


def _render_provider_workload(page) -> None:
    label = getattr(page, "provider_workload_text", None)
    if label is None:
        return
    label.setText(
        TeamProviderWorkloadExplanationService.render_panel(
            tuple(getattr(page, "_provider_rotation_workloads", ()) or ()),
            comparison=getattr(
                page,
                "_provider_rotation_workload_comparison",
                None,
            ),
        )
    )


def _set_provider_workload_evidence(
    page,
    workloads: tuple[TeamProviderRotationWorkload, ...],
    *,
    comparison: TeamProviderRotationWorkloadComparison | None = None,
) -> None:
    normalized = tuple(workloads or ())
    if any(not isinstance(item, TeamProviderRotationWorkload) for item in normalized):
        raise TypeError("provider workload card requires canonical workload results")
    if comparison is not None and not isinstance(
        comparison,
        TeamProviderRotationWorkloadComparison,
    ):
        raise TypeError("provider workload comparison has the wrong result type")
    page._provider_rotation_workloads = normalized
    page._provider_rotation_workload_comparison = comparison
    _render_provider_workload(page)


def _clear_provider_workload_evidence(page) -> None:
    page._provider_rotation_workloads = ()
    page._provider_rotation_workload_comparison = None
    _render_provider_workload(page)


def _comp_init_with_provider_workload(self, parent=None) -> None:
    assert _ORIGINAL_COMP_INIT is not None
    _ORIGINAL_COMP_INIT(self, parent)
    _install_workload_card(self)


def _comp_refresh_with_provider_invalidation(self, *args) -> None:
    _clear_provider_workload_evidence(self)
    assert _ORIGINAL_COMP_REFRESH is not None
    _ORIGINAL_COMP_REFRESH(self, *args)


def _optimization_init_with_provider_workload(self, parent=None) -> None:
    assert _ORIGINAL_OPTIMIZATION_INIT is not None
    _ORIGINAL_OPTIMIZATION_INIT(self, parent)
    _install_workload_card(self)


def _optimization_update_with_provider_invalidation(self) -> None:
    _clear_provider_workload_evidence(self)
    assert _ORIGINAL_OPTIMIZATION_UPDATE is not None
    _ORIGINAL_OPTIMIZATION_UPDATE(self)


def install() -> None:
    global _INSTALLED
    global _ORIGINAL_COMP_INIT, _ORIGINAL_COMP_REFRESH
    global _ORIGINAL_OPTIMIZATION_INIT, _ORIGINAL_OPTIMIZATION_UPDATE
    if _INSTALLED:
        return

    from ui.comp_builder_page import CompBuilderPage
    from ui.optimization_page import OptimizationPage

    _ORIGINAL_COMP_INIT = CompBuilderPage.__init__
    _ORIGINAL_COMP_REFRESH = CompBuilderPage._refresh_coverage
    CompBuilderPage.__init__ = _comp_init_with_provider_workload
    CompBuilderPage._refresh_coverage = _comp_refresh_with_provider_invalidation
    CompBuilderPage.set_provider_workload_evidence = _set_provider_workload_evidence
    CompBuilderPage.clear_provider_workload_evidence = _clear_provider_workload_evidence

    _ORIGINAL_OPTIMIZATION_INIT = OptimizationPage.__init__
    _ORIGINAL_OPTIMIZATION_UPDATE = OptimizationPage._update_team_analysis
    OptimizationPage.__init__ = _optimization_init_with_provider_workload
    OptimizationPage._update_team_analysis = _optimization_update_with_provider_invalidation
    OptimizationPage.set_provider_workload_evidence = _set_provider_workload_evidence
    OptimizationPage.clear_provider_workload_evidence = _clear_provider_workload_evidence
    _INSTALLED = True


__all__ = ["install"]
