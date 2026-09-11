from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

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
            health=("veteran", "1"),
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


def test_runtime_mechanics_page_replaces_strategy_placeholder_with_reviewed_runtime_projection():
    app = QApplication.instance() or QApplication([])
    page = RuntimeMechanicsPage(
        expedition=ExpeditionService(),
        guide_service=_GuideService(),
        runtime_guide_service=_RuntimeGuideService(),
    )

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

    page.close()
    app.processEvents()
