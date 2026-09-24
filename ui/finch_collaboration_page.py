from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from engine.config import DEFAULT_DATABASE, get_data_dir, get_settings_path, get_user_database_path
from services.finch_collaboration_overview_service import (
    FinchCollaborationOverview,
    load_finch_collaboration_overview,
)
from ui.components.foundry_card import FoundryCard
from ui.components.foundry_header import FoundryHeader
from ui.components.foundry_status_bar import FoundryStatusBar
from ui.foundry_page import FoundryPage


_FINCH_COLLAB_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="finch-collaboration",
)


class FinchCollaborationPage(FoundryPage):
    """Read-only command board for all shared Finch operational snapshots."""

    pageRequested = Signal(str)
    workspaceRequested = Signal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._future: Future | None = None
        self._all_rows = ()
        self._rows = ()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll_refresh)
        self._build_ui()

    def _build_ui(self) -> None:
        header = FoundryHeader(
            "Finch Collaboration",
            "Shared operational snapshots across FoundryDock installs",
            "TEAM OPERATIONS",
            "team",
        )
        self.refresh_button = QPushButton("Refresh Finch")
        self.refresh_button.clicked.connect(self.refresh_from_finch)
        header.add_context_widget(self.refresh_button)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Shared", "")
        self.filter_combo.addItem("Changed Since Copy", "changed")
        self.filter_combo.addItem("Not Copied", "not_copied")
        self.filter_combo.addItem("Readiness Gaps", "readiness_gaps")
        self.filter_combo.addItem("Coverage Gaps", "coverage_gaps")
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        header.add_context_widget(self.filter_combo)

        self.open_button = QPushButton("Open Workspace")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_selected_workspace)
        header.add_context_widget(self.open_button)
        self.set_header(header)

        overview = FoundryCard("Collaboration Guide", "feather")
        text = QLabel(
            "Read-only overview: Teams and Raid Plans show copy provenance; Readiness and "
            "Coverage are remote snapshots. Publish and Copy to Local remain in their owning workspaces."
        )
        text.setWordWrap(True)
        overview.addWidget(text)

        attention_row = QHBoxLayout()
        attention_row.setContentsMargins(0, 0, 0, 0)
        attention_row.setSpacing(18)
        self.changed_label = QLabel("Changed since copy: 0")
        self.not_copied_label = QLabel("Not copied: 0")
        self.readiness_gap_label = QLabel("Readiness gaps: 0")
        self.coverage_gap_label = QLabel("Coverage gaps: 0")
        for label in (
            self.changed_label,
            self.not_copied_label,
            self.readiness_gap_label,
            self.coverage_gap_label,
        ):
            label.setProperty("sidebarMeta", True)
            attention_row.addWidget(label)
        attention_row.addStretch()
        overview.addLayout(attention_row)
        self.workspace_layout.addWidget(overview)

        card = FoundryCard("Shared Snapshots", "archive")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["TYPE", "ITEM", "PUBLISHER", "UPDATED", "STATUS", "SUMMARY"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        header_view = self.table.horizontalHeader()
        header_view.setStretchLastSection(True)
        for column in range(5):
            header_view.setSectionResizeMode(
                column,
                header_view.ResizeMode.ResizeToContents,
            )
        self.empty_state_label = QLabel(
            "No shared Finch snapshots yet. Published Teams, Raid Plans, Readiness, and Coverage will appear here."
        )
        self.empty_state_label.setProperty("muted", True)
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_label.setWordWrap(True)
        card.addWidget(self.empty_state_label)
        card.addWidget(self.table)
        self.workspace_layout.addWidget(card, 1)

        self.status = FoundryStatusBar()
        self.set_status(self.status)

    def refresh_from_finch(self) -> None:
        if self._future is not None and not self._future.done():
            self.status.info("Finch collaboration refresh is already running.")
            return

        self.refresh_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.status.info("Refreshing Finch collaboration snapshots…")
        root = get_data_dir()
        self._future = _FINCH_COLLAB_EXECUTOR.submit(
            load_finch_collaboration_overview,
            data_dir=root,
            database_path=get_user_database_path(),
            raid_plans_path=get_user_database_path(),
            settings_path=get_settings_path(),
        )
        self._timer.start()

    def _poll_refresh(self) -> None:
        future = self._future
        if future is None or not future.done():
            return
        self._timer.stop()
        self.refresh_button.setEnabled(True)
        self._future = None

        try:
            overview: FinchCollaborationOverview = future.result()
        except Exception as exc:
            self.status.error(
                f"Finch collaboration refresh failed: {type(exc).__name__}: {exc}"
            )
            return

        self._all_rows = overview.rows
        self.changed_label.setText(f"Changed since copy: {overview.attention.changed}")
        self.not_copied_label.setText(f"Not copied: {overview.attention.not_copied}")
        self.readiness_gap_label.setText(
            f"Readiness gaps: {overview.attention.readiness_gaps}"
        )
        self.coverage_gap_label.setText(
            f"Coverage gaps: {overview.attention.coverage_gaps}"
        )
        self._apply_filter()

        if overview.errors:
            self.status.warning(
                f"Loaded {len(self._rows)} shared snapshot(s); "
                f"{len(overview.errors)} source(s) failed: "
                + " | ".join(overview.errors)
            )
        elif self._rows:
            self.status.success(
                f"Loaded {len(self._rows)} shared Finch snapshot(s)."
            )
        else:
            self.status.info("Finch has no shared collaboration snapshots yet.")

    def _apply_filter(self) -> None:
        tag = str(self.filter_combo.currentData() or "").strip()
        if tag:
            self._rows = tuple(
                row for row in self._all_rows if tag in row.attention_tags
            )
        else:
            self._rows = tuple(self._all_rows)
        self._render_rows()

    def _render_rows(self) -> None:
        self.table.setRowCount(len(self._rows))
        self.empty_state_label.setVisible(not self._rows)
        self.table.setVisible(bool(self._rows))
        for row_index, row in enumerate(self._rows):
            values = (
                row.kind,
                row.item_name,
                row.publisher,
                row.updated,
                row.status,
                row.summary,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row_index, column, item)
        self.table.resizeRowsToContents()
        self.open_button.setEnabled(False)

    def _selection_changed(self) -> None:
        row = self.table.currentRow()
        self.open_button.setEnabled(0 <= row < len(self._rows))

    def _open_selected_workspace(self) -> None:
        row_index = self.table.currentRow()
        if not 0 <= row_index < len(self._rows):
            return
        row = self._rows[row_index]
        if row.route:
            self.workspaceRequested.emit(row.route, row.context_key)


__all__ = ["FinchCollaborationPage"]
