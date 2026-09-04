from __future__ import annotations

"""Add structured value editing and immutable source preview to Encounter Research."""

from PySide6.QtWidgets import QLabel, QPlainTextEdit

from services.encounter_research_review import (
    candidate_source_preview,
    candidate_value_text,
    parse_candidate_value,
    update_candidate_value,
)
from ui.components.foundry_card import FoundryCard


_INSTALLED = False


def _find_card(root, title: str):
    for card in root.findChildren(FoundryCard):
        label = getattr(card, "title_label", None)
        if label is not None and label.text() == title:
            return card
    return None


def install() -> None:
    """Patch the page before Settings constructs its Encounter Research instance."""
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.encounter_research_page import EncounterResearchPage

    original_build_ui = EncounterResearchPage._build_ui
    original_clear_editor = EncounterResearchPage._clear_editor
    original_load_selected = EncounterResearchPage._load_selected_candidate
    original_save_selected = EncounterResearchPage._save_selected_candidate

    def build_ui_with_value_review(self) -> None:
        original_build_ui(self)
        card = _find_card(self, "SELECTED CANDIDATE")
        if card is None:
            return

        value_heading = QLabel("Structured Value (JSON)")
        value_heading.setProperty("sidebarHeading", True)
        card.addWidget(value_heading)

        self.editor_value = QPlainTextEdit()
        self.editor_value.setPlaceholderText(
            'Normalized JSON value, e.g. {"threshold": "50%"}'
        )
        self.editor_value.setMaximumHeight(120)
        self.editor_value.setProperty("parchment", True)
        card.addWidget(self.editor_value)

        preview_heading = QLabel("Source Preview")
        preview_heading.setProperty("sidebarHeading", True)
        card.addWidget(preview_heading)

        self.source_preview = QPlainTextEdit()
        self.source_preview.setReadOnly(True)
        self.source_preview.setMaximumHeight(150)
        self.source_preview.setPlaceholderText(
            "Select a candidate to inspect the archived source context."
        )
        card.addWidget(self.source_preview)

    def clear_editor_with_value(self) -> None:
        original_clear_editor(self)
        if hasattr(self, "editor_value"):
            self.editor_value.clear()
        if hasattr(self, "source_preview"):
            self.source_preview.clear()

    def load_selected_with_source(self) -> None:
        original_load_selected(self)
        candidate = self._selected_candidate()
        if candidate is None:
            return
        if hasattr(self, "editor_value"):
            self.editor_value.setPlainText(candidate_value_text(candidate))
        if not hasattr(self, "source_preview"):
            return
        try:
            preview = candidate_source_preview(self.store, candidate.candidate_id)
        except (KeyError, OSError, ValueError) as exc:
            self.source_preview.setPlainText(f"Source preview unavailable: {exc}")
            return
        header = (
            f"Source: {preview.source_name}\n"
            f"Type: {preview.source_type}   Language: {preview.language}\n"
            f"Stored: {preview.stored_path}\n\n"
        )
        self.source_preview.setPlainText(header + preview.text)

    def save_selected_with_value(self, *, quiet: bool = False) -> bool:
        candidate_id = self._selected_candidate_id()
        if not candidate_id:
            return original_save_selected(self, quiet=quiet)
        if not hasattr(self, "editor_value"):
            return original_save_selected(self, quiet=quiet)

        try:
            parsed_value = parse_candidate_value(self.editor_value.toPlainText())
        except ValueError as exc:
            if not quiet:
                self.status.warning(str(exc))
            return False

        if not original_save_selected(self, quiet=quiet):
            return False
        try:
            update_candidate_value(self.store, candidate_id, parsed_value)
        except (KeyError, ValueError) as exc:
            if not quiet:
                self.status.warning(str(exc))
            return False

        self.refresh()
        if not quiet:
            self.status.success("Candidate review details and structured value saved.")
        return True

    EncounterResearchPage._build_ui = build_ui_with_value_review
    EncounterResearchPage._clear_editor = clear_editor_with_value
    EncounterResearchPage._load_selected_candidate = load_selected_with_source
    EncounterResearchPage._save_selected_candidate = save_selected_with_value
    _INSTALLED = True
