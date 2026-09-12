from __future__ import annotations

from typing import Protocol

from PySide6.QtWidgets import QComboBox

from ui.rotation_generate_action_support import install_rotation_generate_action
from ui.rotation_generate_application_context_provider import (
    RotationGenerateApplicationContextProvider,
)


class _EncounterSummary(Protocol):
    encounter_id: str
    name: str
    content_id: str
    content_name: str


class _EncounterGuideIndex(Protocol):
    def encounter_summaries(self) -> tuple[_EncounterSummary, ...]: ...


class RotationEncounterSelectorSupport:
    """Populate Rotation Builder encounter identity controls from persisted guides.

    This support owns encounter *selection only*. It does not infer demand policies,
    strategy, uptime requirements, cadence obligations, or any other execution truth.
    The selected value is the canonical persisted ``encounter_id`` that a later
    evidence-bundle provider resolves explicitly.

    Installing the selector also installs the common Generate router and its live,
    role-neutral application context provider. That provider still fails closed when
    explicit recovery or encounter-demand policy evidence is absent; installing it does
    not make this selector an owner of those facts. Callers may replace the provider
    afterward through the router's explicit setter.
    """

    def __init__(self, guide_service: _EncounterGuideIndex) -> None:
        self.guide_service = guide_service
        self.summaries: tuple[_EncounterSummary, ...] = ()

    def install(self, page) -> None:
        page.rotation_content_combo = QComboBox()
        page.rotation_boss_combo = QComboBox()
        page.rotation_content_combo.setMinimumWidth(180)
        page.rotation_boss_combo.setMinimumWidth(220)
        page.header.add_context_widget(
            page._context_field("CONTENT", page.rotation_content_combo)
        )
        page.header.add_context_widget(
            page._context_field("BOSS", page.rotation_boss_combo)
        )
        page.rotation_content_combo.currentIndexChanged.connect(
            lambda _index: self.populate_bosses(page)
        )
        self.refresh(page)
        install_rotation_generate_action(page)
        page.set_rotation_generate_canonical_context_provider(
            RotationGenerateApplicationContextProvider()
        )

    def refresh(self, page) -> None:
        self.summaries = tuple(self.guide_service.encounter_summaries())
        current_content = page.rotation_content_combo.currentData()
        current_encounter = page.rotation_boss_combo.currentData()

        page.rotation_content_combo.blockSignals(True)
        page.rotation_content_combo.clear()
        page.rotation_content_combo.addItem("All Content", None)
        seen: set[str] = set()
        for row in self.summaries:
            content_id = str(row.content_id or "").strip()
            if not content_id or content_id in seen:
                continue
            seen.add(content_id)
            label = str(row.content_name or content_id).strip()
            page.rotation_content_combo.addItem(label, content_id)
        page.rotation_content_combo.blockSignals(False)

        if current_content is not None:
            index = page.rotation_content_combo.findData(current_content)
            if index >= 0:
                page.rotation_content_combo.setCurrentIndex(index)
        self.populate_bosses(page, preferred_encounter_id=current_encounter)

    def populate_bosses(self, page, *, preferred_encounter_id=None) -> None:
        content_id = page.rotation_content_combo.currentData()
        rows = tuple(
            row
            for row in self.summaries
            if content_id is None or row.content_id == content_id
        )
        current = preferred_encounter_id or page.rotation_boss_combo.currentData()

        page.rotation_boss_combo.blockSignals(True)
        page.rotation_boss_combo.clear()
        for row in rows:
            encounter_id = str(row.encounter_id or "").strip()
            if not encounter_id:
                continue
            page.rotation_boss_combo.addItem(str(row.name or encounter_id), encounter_id)
        page.rotation_boss_combo.blockSignals(False)

        if current is not None:
            index = page.rotation_boss_combo.findData(current)
            if index >= 0:
                page.rotation_boss_combo.setCurrentIndex(index)
        if page.rotation_boss_combo.count() > 0 and page.rotation_boss_combo.currentIndex() < 0:
            page.rotation_boss_combo.setCurrentIndex(0)

    @staticmethod
    def selected_encounter_id(page) -> str | None:
        value = page.rotation_boss_combo.currentData()
        encounter_id = str(value or "").strip()
        return encounter_id or None


__all__ = ["RotationEncounterSelectorSupport"]
