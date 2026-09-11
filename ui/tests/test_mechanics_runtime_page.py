from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from services.encounter_runtime_guide_projection_service import (
    EncounterGuideRuntimeNote,
    EncounterGuideRuntimeProjection,
    EncounterGuideRuntimeRoleGuidance,
)
from services.expedition_service import ExpeditionService
from ui.mechanics_runtime_page import RuntimeMechanicsPage


class _GuideService:
    def encounter_summaries(self):
        return (
            SimpleNamespace(
                encounter_id="lokkestiiz",
                content_id="sunspire",
                content_name="Sunspire",
                name="Lokkestiiz",
                location="Sunspire",
            ),
        )

    def get(self, encounter_id: str):
        assert encounter_id == "lokkestiiz"
        return SimpleNamespace(
            encounter_id="lokkestiiz",
            content_id="sunspire",
            content_name="Sunspire",
            name="Lokkestiiz",
            summary="Dragon encounter.",
            location="Sunspire",
            health=(("veteran", "1"),),
            source_revision_id="test",
            abilities=(),
            phases=(),
        )


class _RuntimeGuideService:
    def get(self, encounter_id: str) -> EncounterGuideRuntimeProjection:
        assert encounter_id == "lokkestiiz"
        return EncounterGuideRuntimeProjection(
            encounter_id="lokkestiiz",
            notes=(
                EncounterGuideRuntimeNote(
                    key="flight_2_pressure",
                    text="Flight 2 repeatedly carried the strongest sustained pressure.",
                    confidence="repeated_observation",
                ),
            ),
            role_guidance=(
                EncounterGuideRuntimeRoleGuidance(
                    role="healer",
                    priority="high",
                    guidance="Prepare strongest sustained coverage for Flight 2.",
                ),
            ),
            source_labels=("Reviewed Lokke corpus",),
            successful_kills=10,
            reviewed_windows=30,
            limitations=("Observed runtime evidence only.",),
        )


def _page() -> RuntimeMechanicsPage:
    return RuntimeMechanicsPage(
        expedition=ExpeditionService(),
        guide_service=_GuideService(),
        runtime_guide_service=_RuntimeGuideService(),
    )


def test_runtime_mechanics_page_replaces_strategy_placeholder_with_reviewed_runtime_projection():
    app = QApplication.instance() or QApplication([])
    page = _page()

    strategy_index = next(
        index for index in range(page.tabs.count()) if page.tabs.tabText(index) == "STRATEGY"
    )
    assert strategy_index == 2
    assert page.runtime_notes_table.rowCount() == 1
    assert page.runtime_guidance_table.rowCount() == 1
    assert "10 successful clear(s)" in page.runtime_strategy_summary.text()
    assert "not canonical encounter mechanics" in page.runtime_strategy_summary.text()
    assert page.runtime_notes_table.item(0, 0).text().startswith("Flight 2 repeatedly")
    assert page.runtime_guidance_table.item(0, 0).text() == "Healer"
    assert page.runtime_guidance_table.item(0, 1).text() == "High"

    assert page.runtime_strategy_overview_label is not None
    assert "Healer: Prepare strongest sustained coverage for Flight 2." in (
        page.runtime_strategy_overview_label.text()
    )
    assert page.runtime_callouts_label is not None
    assert "Flight 2 repeatedly carried the strongest sustained pressure." in (
        page.runtime_callouts_label.text()
    )
    assert page.runtime_reminders_label is not None
    assert "Healer: Prepare strongest sustained coverage for Flight 2." in (
        page.runtime_reminders_label.text()
    )
    assert "Reviewed runtime sample: 10 successful clear(s)." in (
        page.runtime_reminders_label.text()
    )

    page.close()
    app.processEvents()


def test_runtime_mechanics_page_tolerates_deleted_glance_label():
    app = QApplication.instance() or QApplication([])
    page = _page()

    assert page.runtime_callouts_label is not None
    delete(page.runtime_callouts_label)

    # Regression: support layers may rebuild/delete the base-page placeholder
    # labels. Clearing runtime state must fail closed instead of raising the
    # libshiboken "Internal C++ object already deleted" RuntimeError.
    page._clear_runtime_strategy()

    assert page.runtime_notes_table.rowCount() == 0
    assert page.runtime_guidance_table.rowCount() == 0

    page.close()
    app.processEvents()
