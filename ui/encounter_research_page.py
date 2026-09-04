from __future__ import annotations

"""In-app intake and review surface for encounter research sources."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.encounter_research_store import (
    EncounterResearchCandidate,
    EncounterResearchStore,
)
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_status_bar import FoundryStatusBar


def filter_candidates(
    rows: tuple[EncounterResearchCandidate, ...],
    *,
    content_id: str = "",
    encounter_id: str = "",
    fact_type: str = "",
    status: str = "",
) -> tuple[EncounterResearchCandidate, ...]:
    content = str(content_id or "").strip().casefold()
    encounter = str(encounter_id or "").strip().casefold()
    fact = str(fact_type or "").strip().casefold()
    review = str(status or "").strip().casefold()
    return tuple(
        row
        for row in rows
        if (not content or row.content_id.casefold() == content)
        and (not encounter or row.encounter_id.casefold() == encounter)
        and (not fact or row.fact_type.casefold() == fact)
        and (not review or row.status.casefold() == review)
    )


class EncounterResearchPage(QWidget):
    """Import source material and review deterministic encounter candidates."""

    def __init__(self, parent=None, *, store: EncounterResearchStore | None = None) -> None:
        super().__init__(parent)
        self.store = store or EncounterResearchStore(get_data_dir())
        self._visible_candidates: tuple[EncounterResearchCandidate, ...] = ()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        intake = FoundryCard("ENCOUNTER RESEARCH INTAKE")
        intro = QLabel(
            "Import community guides, notes, HTML, Raid Maps, or ZIP bundles. "
            "BFF extracts conservative review candidates; nothing here writes directly to canonical encounter truth."
        )
        intro.setWordWrap(True)
        intro.setProperty("muted", True)
        intake.addWidget(intro)

        hint_row = QHBoxLayout()
        self.content_hint = QLineEdit()
        self.content_hint.setPlaceholderText("Content id hint, e.g. dreadsail_reef")
        self.encounter_hint = QLineEdit()
        self.encounter_hint.setPlaceholderText("Boss id hint, e.g. reef_guardian")
        self.language_hint = QLineEdit()
        self.language_hint.setPlaceholderText("Language, e.g. en")
        hint_row.addWidget(self.content_hint)
        hint_row.addWidget(self.encounter_hint)
        hint_row.addWidget(self.language_hint)
        intake.addLayout(hint_row)

        buttons = QHBoxLayout()
        self.add_files_button = QPushButton("Add Files")
        self.add_zip_button = QPushButton("Add ZIP")
        self.refresh_button = QPushButton("Refresh")
        buttons.addWidget(self.add_files_button)
        buttons.addWidget(self.add_zip_button)
        buttons.addStretch(1)
        buttons.addWidget(self.refresh_button)
        intake.addLayout(buttons)
        root.addWidget(intake)

        stats = FoundryCard("RESEARCH STATUS")
        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        stats.addWidget(self.stats_label)
        root.addWidget(stats)

        review = FoundryCard("CANDIDATE REVIEW")
        filters = QHBoxLayout()
        self.content_filter = QComboBox()
        self.encounter_filter = QComboBox()
        self.type_filter = QComboBox()
        self.status_filter = QComboBox()
        for combo, label in (
            (self.content_filter, "All content"),
            (self.encounter_filter, "All bosses"),
            (self.type_filter, "All types"),
            (self.status_filter, "All statuses"),
        ):
            combo.addItem(label, "")
            filters.addWidget(combo)
        review.addLayout(filters)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ("Status", "Content", "Boss", "Type", "Key", "Value", "Evidence")
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        review.addWidget(self.table)

        review_buttons = QHBoxLayout()
        self.approve_button = QPushButton("Approve")
        self.reject_button = QPushButton("Reject")
        self.defer_button = QPushButton("Defer")
        self.pending_button = QPushButton("Return to Pending")
        self.approve_button.setProperty("primary", True)
        review_buttons.addWidget(self.approve_button)
        review_buttons.addWidget(self.reject_button)
        review_buttons.addWidget(self.defer_button)
        review_buttons.addWidget(self.pending_button)
        review_buttons.addStretch(1)
        review.addLayout(review_buttons)
        root.addWidget(review, 1)

        self.status = FoundryStatusBar()
        self.status.info("Encounter Research ready.")
        root.addWidget(self.status)

        self.add_files_button.clicked.connect(self._add_files)
        self.add_zip_button.clicked.connect(self._add_zip)
        self.refresh_button.clicked.connect(self.refresh)
        self.approve_button.clicked.connect(lambda: self._set_selected_status("approved"))
        self.reject_button.clicked.connect(lambda: self._set_selected_status("rejected"))
        self.defer_button.clicked.connect(lambda: self._set_selected_status("deferred"))
        self.pending_button.clicked.connect(lambda: self._set_selected_status("pending"))
        for combo in (
            self.content_filter,
            self.encounter_filter,
            self.type_filter,
            self.status_filter,
        ):
            combo.currentIndexChanged.connect(lambda _index: self._render_candidates())

    def _import_kwargs(self) -> dict[str, str]:
        return {
            "content_hint": self.content_hint.text().strip(),
            "encounter_hint": self.encounter_hint.text().strip(),
            "language": self.language_hint.text().strip() or "unknown",
        }

    def _add_files(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Encounter Research Sources",
            "",
            "Encounter Sources (*.txt *.md *.html *.htm *.png *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if not filenames:
            return
        imported = 0
        try:
            for filename in filenames:
                imported += len(self.store.import_path(Path(filename), **self._import_kwargs()))
        except (OSError, ValueError) as exc:
            self.status.warning(f"Encounter source import stopped: {exc}")
        else:
            self.status.success(f"Imported {imported} encounter research source(s).")
        self.refresh()

    def _add_zip(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Add Encounter Research ZIP",
            "",
            "ZIP Archives (*.zip)",
        )
        if not filename:
            return
        try:
            rows = self.store.import_path(Path(filename), **self._import_kwargs())
        except (OSError, ValueError) as exc:
            self.status.warning(f"Encounter ZIP import failed: {exc}")
        else:
            self.status.success(f"Imported {len(rows)} supported source(s) from ZIP.")
        self.refresh()

    @staticmethod
    def _reset_combo(combo: QComboBox, first_label: str, values: set[str]) -> None:
        current = str(combo.currentData() or "")
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(first_label, "")
        for value in sorted(v for v in values if v):
            combo.addItem(value, value)
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def refresh(self) -> None:
        rows = self.store.candidates()
        self._reset_combo(self.content_filter, "All content", {row.content_id for row in rows})
        self._reset_combo(self.encounter_filter, "All bosses", {row.encounter_id for row in rows})
        self._reset_combo(self.type_filter, "All types", {row.fact_type for row in rows})
        self._reset_combo(self.status_filter, "All statuses", {row.status for row in rows})

        counts = self.store.counts()
        self.stats_label.setText(
            f"Sources: {counts['sources']}   •   Candidates: {counts['candidates']}   •   "
            f"Pending: {counts['pending']}   •   Approved: {counts['approved']}   •   "
            f"Deferred: {counts['deferred']}   •   Rejected: {counts['rejected']}"
        )
        self._render_candidates()

    def _render_candidates(self) -> None:
        rows = filter_candidates(
            self.store.candidates(),
            content_id=str(self.content_filter.currentData() or ""),
            encounter_id=str(self.encounter_filter.currentData() or ""),
            fact_type=str(self.type_filter.currentData() or ""),
            status=str(self.status_filter.currentData() or ""),
        )
        self._visible_candidates = rows
        self.table.setRowCount(len(rows))
        for row_index, candidate in enumerate(rows):
            values = (
                candidate.status,
                candidate.content_id or "Unassigned",
                candidate.encounter_id or "Unassigned",
                candidate.fact_type,
                candidate.fact_key,
                str(candidate.value),
                candidate.evidence_text,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
                )
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, candidate.candidate_id)
                self.table.setItem(row_index, column, item)
        self.table.resizeRowsToContents()

    def _selected_candidate_id(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        item = self.table.item(row, 0)
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item is not None else ""

    def _set_selected_status(self, status: str) -> None:
        candidate_id = self._selected_candidate_id()
        if not candidate_id:
            self.status.warning("Select a candidate row first.")
            return
        try:
            self.store.set_candidate_status(candidate_id, status)
        except (KeyError, ValueError) as exc:
            self.status.warning(str(exc))
            return
        self.status.success(f"Candidate marked {status}.")
        self.refresh()
