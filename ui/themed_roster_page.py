from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QPushButton

from services.accessibility_preferences import AccessibilityPreferences
from services.share_document_export import ShareDocumentExporter
from ui.roster_page import RosterPage as BaseRosterPage


class RosterPage(BaseRosterPage):
    """Roster page with theme-aware human sharing."""

    def _build_ui(self):
        super()._build_ui()
        self.export_share_button = QPushButton("Export / Share")
        self.export_share_button.setProperty("primary", True)
        self.export_share_button.setToolTip(
            "Export the visible raid assignments and personnel roster as a themed PDF."
        )
        self.export_share_button.clicked.connect(self._export_roster_pdf)
        self.header.add_context_widget(self.export_share_button)

    def _visible_assignment_rows(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        table = getattr(self, "assignment_table", None)
        if table is None:
            return rows

        for row in range(table.rowCount()):
            def text(column: int) -> str:
                item = table.item(row, column)
                return item.text().strip() if item is not None else ""

            rows.append({
                "player": text(0),
                "role": text(1),
                "class": text(2),
                "build": text(3),
                "primary": text(4),
                "secondary": text(5),
                "gear": text(6),
                "notes": text(7),
                "ready": text(8),
            })
        return rows

    def _export_roster_pdf(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Roster",
            "raid_roster.pdf",
            "Share PDF (*.pdf)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.casefold() != ".pdf":
            path = path.with_suffix(".pdf")

        title = "Raid Roster"
        if hasattr(self, "view_combo"):
            view = self.view_combo.currentText().strip()
            if view:
                title = view

        try:
            theme_name = AccessibilityPreferences().visual_theme()
            ShareDocumentExporter().export_roster(
                self.members,
                path,
                assignments=self._visible_assignment_rows(),
                title=title,
                theme_name=theme_name,
            )
            self.status.success(f"Exported themed roster to {path}")
        except Exception as exc:
            self.status.error(f"Roster export failed: {exc}")
