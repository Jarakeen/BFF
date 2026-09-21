from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget, QTableWidgetItem

from engine.config import DEFAULT_DATABASE, get_data_dir
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

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._future: Future | None = None
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

        self.open_button = QPushButton("Open Workspace")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_selected_workspace)
        header.add_context_widget(self.open_button)
        self.set_header(header)

        note = FoundryCard("How This Board Works", "feather")
        text = QLabel(
            "This page is a read-only overview. Teams and Raid Plans show copy provenance; "
            "Readiness and Coverage are remote snapshots only. Publishing and Copy to Local "
            "still happen in their owning workspaces."
        )
        text.setWordWrap(True)
        note.addWidget(text)
        self.workspace_layout.addWidget(note)

        card = FoundryCard("Shared Snapshots", "team")
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
            database_path=DEFAULT_DATABASE,
            raid_plans_path=root / "raid_plans.json",
            settings_path=Path("settings.json"),
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

        self._rows = overview.rows
        self.table.setRowCount(len(self._rows))
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

    def _selection_changed(self) -> None:
        row = self.table.currentRow()
        self.open_button.setEnabled(0 <= row < len(self._rows))

    def _open_selected_workspace(self) -> None:
        row_index = self.table.currentRow()
        if not 0 <= row_index < len(self._rows):
            return
        route = self._rows[row_index].route
        if route:
            self.pageRequested.emit(route)


__all__ = ["FinchCollaborationPage"]
