from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from services.accessibility_preferences import AccessibilityPreferences
from services.share_document_export import ShareDocumentExporter
from ui.builds_page import BuildsPage as BaseBuildsPage


class BuildsPage(BaseBuildsPage):
    """Builds page with human-readable, theme-aware share exports."""

    def _build_ui(self):
        super()._build_ui()
        try:
            self.export_button.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.export_button.setText("Export / Share")
        self.export_button.setToolTip(
            "Export a themed PDF for people, or CSV for data interchange."
        )
        self.export_button.clicked.connect(self._export_builds)

    def _export_builds(self):
        folder = ""
        try:
            folder = self.settings_service.load().get("BuildsExportFolder", "") or ""
        except Exception:
            pass

        start = str(Path(folder) / "raid_builds.pdf") if folder else "raid_builds.pdf"
        filename, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Builds",
            start,
            "Share PDF (*.pdf);;CSV Data (*.csv)",
        )
        if not filename:
            return

        path = Path(filename)
        if "CSV" in selected_filter or path.suffix.casefold() == ".csv":
            if path.suffix.casefold() != ".csv":
                path = path.with_suffix(".csv")
            try:
                self.build_service.export_csv(self.roster, path)
                self.status.success(f"Exported build data to {path}")
            except Exception as exc:
                self.status.error(f"Export failed: {exc}")
            return

        if path.suffix.casefold() != ".pdf":
            path = path.with_suffix(".pdf")
        try:
            theme_name = AccessibilityPreferences().visual_theme()
            ShareDocumentExporter().export_builds(
                self.roster,
                path,
                theme_name=theme_name,
            )
            self.status.success(f"Exported themed build dossier to {path}")
        except Exception as exc:
            self.status.error(f"PDF export failed: {exc}")
