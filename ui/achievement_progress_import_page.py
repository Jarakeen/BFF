from __future__ import annotations

"""Local achievement and collectible progress import/export workspace."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from engine.config import get_data_dir
from services.achievement_progress_export_service import AchievementProgressExportService
from services.achievement_progress_service import AchievementProgressService
from services.eso_achievement_database_service import EsoAchievementDatabaseService
from services.google_sheet_progress_importer import GoogleSheetProgressImporter
from services.local_achievement_workbook_service import LocalAchievementWorkbookService
from services.local_collectible_progress_importer import LocalCollectibleProgressImporter
from services.local_collectible_workbook_service import LocalCollectibleWorkbookService
from services.profiled_collectible_service import ProfiledCollectibleService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar


class AchievementProgressImportPage(QWidget):
    """Preview and import legacy/local achievement and collectible workbooks safely."""

    PEOPLE = ("Jarakeen", "Rylo")

    def __init__(self, parent=None, *, embedded: bool = False):
        super().__init__(parent)
        self.embedded = bool(embedded)
        data_dir = get_data_dir()
        self.achievement_data = EsoAchievementDatabaseService(data_dir / "eso.db")
        self.achievement_progress = AchievementProgressService(data_dir / "achievement_progress.json")
        self.collectible_progress = ProfiledCollectibleService(data_dir / "eso.db")
        self.workbooks = LocalAchievementWorkbookService()
        self.collectible_workbooks = LocalCollectibleWorkbookService()
        self.importer = GoogleSheetProgressImporter(
            self.achievement_data,
            self.achievement_progress,
            self.collectible_progress,
        )
        self.collectible_importer = LocalCollectibleProgressImporter(self.collectible_progress)
        self.exporter = AchievementProgressExportService(
            self.achievement_data,
            self.achievement_progress,
        )
        self._source_path: Path | None = None
        self._snapshots = {}
        self._previews = {}
        self._collectible_snapshots = {}
        self._collectible_previews = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0) if self.embedded else root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        if not self.embedded:
            self.header = FoundryHeader(
                title="Progress Import & Export",
                subtitle="Bring the old progress workbook forward, then use canonical IDs from here on.",
                department="Research",
                icon="download",
            )
            root.addWidget(self.header)
        else:
            root.addWidget(
                self._note(
                    "Import legacy achievement and collectible progress without Google API access, preview every change before writing it, "
                    "or export a clean canonical achievement workbook/CSV for future backups and round trips."
                )
            )

        source_card = FoundryCard("SOURCE WORKBOOK")
        source_row = QHBoxLayout()
        self.source_label = QLabel("No workbook selected")
        self.source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.choose_button = QPushButton("Choose Spreadsheet…")
        self.choose_button.clicked.connect(self.choose_workbook)
        source_row.addWidget(self.source_label, 1)
        source_row.addWidget(self.choose_button)
        source_card.addLayout(source_row)
        source_card.addWidget(
            self._note(
                "Legacy BFF progress is supported: A = Rylo, B = Jarakeen, C = name; achievement rows also use F = points. "
                "Standalone collectible sheets are detected conservatively and exact-matched to canonical collectible names."
            )
        )
        root.addWidget(source_card)

        preview_card = FoundryCard("IMPORT PREVIEW")
        selector_row = QHBoxLayout()
        self.profile_checks: dict[str, QCheckBox] = {}
        for person in self.PEOPLE:
            check = QCheckBox(f"Import {person}")
            check.setChecked(True)
            self.profile_checks[person] = check
            selector_row.addWidget(check)
        selector_row.addStretch(1)
        self.import_button = QPushButton("Import Selected Profiles")
        self.import_button.setProperty("primary", True)
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.import_selected)
        selector_row.addWidget(self.import_button)
        preview_card.addLayout(selector_row)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(240)
        self.preview_text.setPlaceholderText("Choose a spreadsheet to preview the import. Nothing is written during preview.")
        preview_card.addWidget(self.preview_text)
        root.addWidget(preview_card, 1)

        export_card = FoundryCard("CANONICAL EXPORTS")
        export_card.addWidget(
            self._note(
                "Achievement exports are normalized and profile-aware. Collectible ownership already lives canonically in SQLite and can be "
                "exported from the Collections tools; legacy workbook collectible rows are only a migration source."
            )
        )
        export_row = QHBoxLayout()
        self.export_xlsx_button = QPushButton("Export Workbook (.xlsx)")
        self.export_csv_button = QPushButton("Export CSV")
        self.export_xlsx_button.clicked.connect(self.export_xlsx)
        self.export_csv_button.clicked.connect(self.export_csv)
        export_row.addWidget(self.export_xlsx_button)
        export_row.addWidget(self.export_csv_button)
        export_row.addStretch(1)
        export_card.addLayout(export_row)
        root.addWidget(export_card)

        self.status = FoundryStatusBar()
        self.status.info("Choose a workbook to begin. Preview is read-only.")
        root.addWidget(self.status)

    @staticmethod
    def _note(text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setProperty("muted", True)
        return label

    def choose_workbook(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Progress Spreadsheet",
            "",
            "Excel Workbooks (*.xlsx *.xlsm)",
        )
        if not filename:
            return
        self._source_path = Path(filename)
        self.source_label.setText(str(self._source_path))
        self.preview_workbook()

    def preview_workbook(self) -> None:
        if self._source_path is None:
            return
        self._snapshots.clear()
        self._previews.clear()
        self._collectible_snapshots.clear()
        self._collectible_previews.clear()
        lines = [f"Workbook: {self._source_path}", ""]
        try:
            for person in self.PEOPLE:
                snapshot = self.workbooks.read_person(self._source_path, person)
                preview = self.importer.preview_checked(snapshot, profile=person)
                collectible_snapshot = self.collectible_workbooks.read_person(self._source_path, person)
                collectible_preview = self.collectible_importer.preview_checked(
                    collectible_snapshot, profile=person
                )
                self._snapshots[person] = snapshot
                self._previews[person] = preview
                self._collectible_snapshots[person] = collectible_snapshot
                self._collectible_previews[person] = collectible_preview
                lines.extend(self._preview_lines(preview, collectible_preview))
        except Exception as exc:
            self.preview_text.setPlainText(f"Preview failed:\n{exc}")
            self.import_button.setEnabled(False)
            self.status.error(f"Workbook preview failed: {exc}")
            return

        self.preview_text.setPlainText("\n".join(lines))
        self.import_button.setEnabled(bool(self._snapshots))
        self.status.success("Preview complete. No progress has been changed.")

    @staticmethod
    def _preview_lines(preview, collectible_preview) -> list[str]:
        lines = [
            f"{preview.source_person}",
            "  Achievements",
            f"    Rows found: {preview.sheet_rows}",
            f"    Checked rows: {preview.checked_rows}",
            f"    Canonical matches: {preview.matched_achievements}",
            f"    Achievement-reward collectibles: {preview.collectible_rewards}",
            f"    Unmatched names: {len(preview.unresolved_names)}",
            f"    Ambiguous names: {len(preview.ambiguous_names)}",
            f"    Missing legacy tabs: {len(preview.missing_tabs)}",
            "  Standalone Collectibles",
            f"    Tabs scanned: {len(collectible_preview.scanned_tabs)}",
            f"    Rows found: {collectible_preview.sheet_rows}",
            f"    Checked rows: {collectible_preview.checked_rows}",
            f"    Canonical matches: {collectible_preview.matched_collectibles}",
            f"    Unmatched names: {len(collectible_preview.unresolved_names)}",
            f"    Ambiguous names: {len(collectible_preview.ambiguous_names)}",
        ]
        if collectible_preview.scanned_tabs:
            lines.append("    Sheets: " + "; ".join(collectible_preview.scanned_tabs))
        if preview.unresolved_names:
            lines.append("    Achievement unmatched: " + "; ".join(preview.unresolved_names[:20]))
        if preview.ambiguous_names:
            lines.append("    Achievement ambiguous: " + "; ".join(preview.ambiguous_names[:20]))
        if collectible_preview.unresolved_names:
            lines.append("    Collectible unmatched: " + "; ".join(collectible_preview.unresolved_names[:20]))
            if len(collectible_preview.unresolved_names) > 20:
                lines.append(f"    …and {len(collectible_preview.unresolved_names) - 20} more collectible names")
        if collectible_preview.ambiguous_names:
            lines.append("    Collectible ambiguous: " + "; ".join(collectible_preview.ambiguous_names[:20]))
        lines.append("")
        return lines

    def _selected_people(self) -> list[str]:
        return [person for person, check in self.profile_checks.items() if check.isChecked()]

    def _confirm_import(self, people: list[str]) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Are you really, really, really sure?")
        box.setText("Are you really, really, really sure?")
        box.setInformativeText(
            "This will merge checked achievements and standalone collectibles into: "
            + ", ".join(people)
            + ". Achievement-reward collectibles with canonical links will also be marked owned. "
            "Nothing is deleted, and unmatched or ambiguous names will not be guessed."
        )
        yes_button = box.addButton(
            "Yes, I am really really really sure",
            QMessageBox.ButtonRole.AcceptRole,
        )
        cancel_button = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel_button)
        box.setEscapeButton(cancel_button)
        box.exec()
        return box.clickedButton() is yes_button

    def import_selected(self) -> None:
        people = self._selected_people()
        if not people:
            self.status.warning("Select at least one profile to import.")
            return
        if any(
            person not in self._snapshots or person not in self._collectible_snapshots
            for person in people
        ):
            self.status.warning("Preview the workbook before importing.")
            return
        if not self._confirm_import(people):
            self.status.info("Import cancelled. Local progress was not changed.")
            return

        self.import_button.setEnabled(False)
        self.import_button.setText("Importing…")
        self.status.info("Import in progress. Please wait…")
        QApplication.processEvents()

        summaries = []
        try:
            for person in people:
                report = self.importer.import_checked(self._snapshots[person], profile=person)
                collectible_report = self.collectible_importer.import_checked(
                    self._collectible_snapshots[person], profile=person
                )
                summaries.append(
                    f"{person}: {report.matched_achievements} achievements matched, "
                    f"{report.achievements_added} newly added; "
                    f"{report.collectible_rewards_marked} reward collectibles + "
                    f"{collectible_report.collectibles_marked_owned} standalone collectibles marked owned"
                )
        except Exception as exc:
            self.import_button.setText("Import Selected Profiles")
            self.import_button.setEnabled(bool(self._snapshots))
            self.status.error(f"Import failed: {exc}")
            QMessageBox.critical(
                self,
                "Progress Import Failed",
                f"The import did not finish successfully.\n\n{exc}",
            )
            return

        completion_text = "\n".join(summaries)
        self.preview_workbook()
        self.import_button.setText("Import Selected Profiles")
        self.import_button.setEnabled(bool(self._snapshots))
        self.status.success("Import complete. " + " | ".join(summaries))
        QMessageBox.information(
            self,
            "Progress Import Complete",
            "Import complete.\n\n" + completion_text,
        )

    def export_xlsx(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Achievement Progress Workbook",
            "Foundry_Achievement_Progress.xlsx",
            "Excel Workbook (*.xlsx)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.casefold() != ".xlsx":
            path = path.with_suffix(".xlsx")
        try:
            written = self.exporter.export_xlsx(path)
        except Exception as exc:
            self.status.error(f"Workbook export failed: {exc}")
            return
        self.status.success(f"Exported canonical workbook: {written}")

    def export_csv(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Achievement Progress CSV",
            "Foundry_Achievement_Progress.csv",
            "CSV Files (*.csv)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.casefold() != ".csv":
            path = path.with_suffix(".csv")
        try:
            written = self.exporter.export_csv(path)
        except Exception as exc:
            self.status.error(f"CSV export failed: {exc}")
            return
        self.status.success(f"Exported canonical CSV: {written}")
