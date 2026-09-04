from __future__ import annotations

"""Install Encounter Research alongside achievement progress data management."""

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from ui.achievement_progress_import_page import AchievementProgressImportPage
from ui.components.foundry_card import FoundryCard
from ui.encounter_research_page import EncounterResearchPage
from ui.encounter_research_value_support import install as install_value_review


_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    # Patch candidate value/source review before Settings constructs the page.
    install_value_review()

    from ui.settings_page import SettingsPage

    def data_management_page_with_research(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        heading = FoundryCard("DATA MANAGEMENT")
        heading.addWidget(
            self._muted_note(
                "Import profile progress or research encounter sources here. "
                "Encounter Research stages review candidates separately from canonical ESO encounter truth."
            )
        )
        layout.addWidget(heading)

        tabs = QTabWidget()
        self.achievement_progress_io = AchievementProgressImportPage(self, embedded=True)
        self.encounter_research = EncounterResearchPage(self)
        tabs.addTab(self.achievement_progress_io, "ACHIEVEMENT PROGRESS")
        tabs.addTab(self.encounter_research, "ENCOUNTER RESEARCH")
        layout.addWidget(tabs, 1)
        self.data_management_tabs = tabs
        return page

    SettingsPage._data_management_page = data_management_page_with_research
    _INSTALLED = True
