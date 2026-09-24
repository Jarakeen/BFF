from __future__ import annotations

"""Review workspace for cross-pull Minor Brittle uptime."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.brittle_uptime_service import BrittleUptimeService
from services.esologs_client import EsoLogsApiError, EsoLogsClient
from services.settings_service import SettingsService
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


def _duration(seconds: float) -> str:
    total = max(0, int(round(float(seconds or 0.0))))
    minutes, second = divmod(total, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minute:02d}:{second:02d}"
    return f"{minute:02d}:{second:02d}"


class BrittleUptimePage(FoundryPage):
    """Read-only Minor Brittle comparison desk backed by the ESO Logs API."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.settings_service = SettingsService(Path("settings.json"))
        self._report = None
        self._build_ui()

    def _build_client(self) -> EsoLogsClient:
        settings = self.settings_service.load()
        return EsoLogsClient(
            client_id=settings.get("EsoLogsClientId", ""),
            client_secret=settings.get("EsoLogsClientSecret", ""),
        )

    def _build_ui(self) -> None:
        self.header = FoundryHeader(
            title="Brittle Uptime",
            subtitle="Minor Brittle evidence from ESO Logs, pull by pull and provider by provider.",
            department="RAID • REVIEW",
            icon="archive",
        )
        self.set_header(self.header)

        inputs = FoundryCard("Log Scope", "search")
        row = QHBoxLayout()
        row.setSpacing(8)

        self.report_input = QLineEdit()
        self.report_input.setPlaceholderText("ESO Logs report URL or code")
        self.report_input.returnPressed.connect(self.load_report)
        row.addWidget(self.report_input, 3)

        self.fights_input = QLineEdit()
        self.fights_input.setPlaceholderText("Fight IDs, e.g. 6,21,25,32")
        self.fights_input.returnPressed.connect(self.load_report)
        row.addWidget(self.fights_input, 2)

        self.kills_only = QCheckBox("Kills only")
        self.kills_only.setChecked(True)
        row.addWidget(self.kills_only)

        self.load_button = QPushButton("Load Brittle")
        self.load_button.setProperty("primary", True)
        self.load_button.clicked.connect(self.load_report)
        row.addWidget(self.load_button)
        inputs.addLayout(row)

        note = QLabel(
            "Raid uptime is the ESO Logs enemy-debuff uptime for Minor Brittle. "
            "Duplicate Minor Brittle ability IDs are de-duplicated instead of summed. "
            "Provider rows show source-attributed uptime and can overlap, so provider percentages "
            "are evidence of contribution, not pieces that must add to the raid total."
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)
        inputs.addWidget(note)
        self.workspace_layout.addWidget(inputs)

        summary = FoundryCard("Kill Comparison", "compass")
        summary_row = QHBoxLayout()
        self.count_label = QLabel("Fights\n—")
        self.average_label = QLabel("Average\n—")
        self.best_label = QLabel("Best\n—")
        self.low_label = QLabel("Lowest\n—")
        for widget in (self.count_label, self.average_label, self.best_label, self.low_label):
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget.setProperty("heroTitle", True)
            summary_row.addWidget(widget, 1)
        summary.addLayout(summary_row)

        self.fight_table = QTableWidget(0, 8)
        self.fight_table.setHorizontalHeaderLabels(
            ["FIGHT", "ENCOUNTER", "RESULT", "DURATION", "BRITTLE TIME", "UPTIME", "PROVIDERS", "TOP SOURCE"]
        )
        self.fight_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fight_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fight_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.fight_table.verticalHeader().setVisible(False)
        self.fight_table.itemSelectionChanged.connect(self._show_selected_providers)
        self.fight_table.horizontalHeader().setStretchLastSection(True)
        summary.addWidget(self.fight_table)
        self.workspace_layout.addWidget(summary)

        detail = FoundryCard("Selected Pull · Provider Evidence", "clipboard")
        self.provider_heading = QLabel("Select a pull")
        self.provider_heading.setProperty("heroTitle", True)
        detail.addWidget(self.provider_heading)

        self.provider_table = QTableWidget(0, 5)
        self.provider_table.setHorizontalHeaderLabels(
            ["PLAYER", "ROLE", "BRITTLE TIME", "SOURCE UPTIME", "ACTOR ID"]
        )
        self.provider_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.provider_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.provider_table.verticalHeader().setVisible(False)
        self.provider_table.horizontalHeader().setStretchLastSection(True)
        detail.addWidget(self.provider_table)

        provider_note = QLabel(
            "Source uptime can overlap when multiple players apply Minor Brittle. "
            "Use raid uptime for whether the boss had the debuff; use provider rows to establish who contributed."
        )
        provider_note.setWordWrap(True)
        provider_note.setProperty("muted", True)
        detail.addWidget(provider_note)
        self.workspace_layout.addWidget(detail)

        self.status_bar = FoundryStatusBar()
        self.set_status(self.status_bar)

    def _fight_ids(self) -> tuple[int, ...]:
        text = self.fights_input.text().strip()
        if not text:
            return ()
        values: list[int] = []
        for piece in text.replace(";", ",").split(","):
            cleaned = piece.strip()
            if not cleaned:
                continue
            if not cleaned.isdigit():
                raise ValueError(f"Invalid fight ID: {cleaned}")
            values.append(int(cleaned))
        return tuple(values)

    def load_report(self) -> None:
        report_code = self.report_input.text().strip()
        if not report_code:
            self.status_bar.warning("Enter an ESO Logs report URL or report code.")
            return

        self.load_button.setEnabled(False)
        self.status_bar.info("Loading Minor Brittle evidence from ESO Logs…")
        try:
            service = BrittleUptimeService(self._build_client())
            self._report = service.analyze(
                report_code,
                fight_ids=self._fight_ids(),
                kills_only=self.kills_only.isChecked(),
            )
            self._render_report()
            self.status_bar.success(
                f"Loaded {len(self._report.fights)} fight(s) from {self._report.report_code}."
            )
        except (EsoLogsApiError, ValueError) as exc:
            self._report = None
            self._clear_tables()
            self.status_bar.error(str(exc))
        except Exception as exc:
            self._report = None
            self._clear_tables()
            self.status_bar.error(f"Brittle analysis failed: {exc}")
        finally:
            self.load_button.setEnabled(True)

    def _clear_tables(self) -> None:
        self.fight_table.setRowCount(0)
        self.provider_table.setRowCount(0)
        self.provider_heading.setText("Select a pull")
        self.count_label.setText("Fights\n—")
        self.average_label.setText("Average\n—")
        self.best_label.setText("Best\n—")
        self.low_label.setText("Lowest\n—")

    def _render_report(self) -> None:
        report = self._report
        if report is None:
            self._clear_tables()
            return

        self.count_label.setText(f"Fights\n{len(report.fights)}")
        self.average_label.setText(f"Average\n{report.average_percent:.1f}%")
        self.best_label.setText(f"Best\n{report.best_percent:.1f}%")
        self.low_label.setText(f"Lowest\n{report.lowest_percent:.1f}%")

        self.fight_table.setRowCount(len(report.fights))
        for row_index, fight in enumerate(report.fights):
            top_source = fight.providers[0].actor_label if fight.providers else "—"
            values = (
                str(fight.fight_id),
                fight.fight_name,
                "KILL" if fight.kill else "WIPE",
                _duration(fight.duration_seconds),
                f"{fight.brittle_seconds:.1f}s",
                f"{fight.brittle_percent:.1f}%",
                str(len(fight.providers)),
                top_source,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, row_index)
                self.fight_table.setItem(row_index, column, item)

        self.fight_table.resizeColumnsToContents()
        self.fight_table.resizeRowsToContents()
        if report.fights:
            self.fight_table.selectRow(0)
        else:
            self.provider_table.setRowCount(0)
            self.provider_heading.setText("No matching fights")

    def _show_selected_providers(self) -> None:
        if self._report is None:
            return
        selected = self.fight_table.selectionModel().selectedRows()
        if not selected:
            return
        row_index = selected[0].row()
        if row_index < 0 or row_index >= len(self._report.fights):
            return

        fight = self._report.fights[row_index]
        self.provider_heading.setText(
            f"Fight {fight.fight_id} · {fight.fight_name} · raid uptime {fight.brittle_percent:.1f}%"
        )
        self.provider_table.setRowCount(len(fight.providers))
        for row, provider in enumerate(fight.providers):
            values = (
                provider.actor_label,
                provider.role,
                f"{provider.uptime_seconds:.1f}s",
                f"{provider.uptime_percent:.1f}%",
                str(provider.actor_id),
            )
            for column, value in enumerate(values):
                self.provider_table.setItem(row, column, QTableWidgetItem(value))
        self.provider_table.resizeColumnsToContents()
        self.provider_table.resizeRowsToContents()


__all__ = ["BrittleUptimePage"]
