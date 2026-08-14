# ui/archive_log.py
from __future__ import annotations


import json
import random
from datetime import datetime
from pathlib import Path
import re
from services.tamriel_calendar import get_tamriel_date 


from PySide6.QtCore import Qt, QTimer, QAbstractTableModel, QModelIndex, QSize
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)



def _build_archive_log_page(self) -> QWidget:
        page = QWidget()
        outer_layout = QHBoxLayout(page)

        # --- Left column: this session's live logs ---
        left_column = QVBoxLayout()

        intro = QLabel("What's actually being saved when you push buttons on Stream Events.")
        left_column.addWidget(intro)

        marker_box = QGroupBox("Marker Log (Pull Starts, Wipes, Boss Clears, BRB, Field Notes, Incidents)")
        marker_layout = QVBoxLayout(marker_box)
        self.marker_log_view = QTextEdit()
        self.marker_log_view.setReadOnly(True)
        self.marker_log_view.setPlaceholderText("Click Refresh to load this session's marker log.")
        marker_layout.addWidget(self.marker_log_view)
        left_column.addWidget(marker_box, 2)

        boss_box = QGroupBox("Boss Log (from Boss Clears)")
        boss_layout = QVBoxLayout(boss_box)
        self.boss_log_view = QTextEdit()
        self.boss_log_view.setReadOnly(True)
        self.boss_log_view.setPlaceholderText("Click Refresh to load this session's boss log.")
        boss_layout.addWidget(self.boss_log_view)
        left_column.addWidget(boss_box, 1)

        notes_box = QGroupBox("Session Notes (included in the consolidated report)")
        notes_layout = QVBoxLayout(notes_box)
        self.session_notes_edit = QTextEdit()
        self.session_notes_edit.setPlaceholderText("How'd the run go? Anything worth remembering...")
        notes_layout.addWidget(self.session_notes_edit)
        left_column.addWidget(notes_box, 1)

        actions = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        archive_btn = QPushButton("Save to Archive")
        clear_btn = QPushButton("Clear")
        refresh_btn.clicked.connect(self.refresh_archive_log)
        clear_btn.clicked.connect(self.clear_archive)
        archive_btn.clicked.connect(self.archive_current_run)
        actions.addWidget(clear_btn)
        actions.addWidget(refresh_btn)
        actions.addWidget(archive_btn)
        left_column.addLayout(actions)

        outer_layout.addLayout(left_column, 2)

        # --- Right column: browse past archived sessions ---
        right_column = QVBoxLayout()
        browser_box = QGroupBox("Archive Browser")
        browser_layout = QVBoxLayout(browser_box)

        search_row = QHBoxLayout()
        self.archive_search_edit = QLineEdit()
        self.archive_search_edit.setPlaceholderText("Search by serial, boss, location, date...")
        self.archive_search_edit.textChanged.connect(self.filter_archive_browser)
        search_row.addWidget(self.archive_search_edit)
        browser_layout.addLayout(search_row)

        self.archive_browser_list = QListWidget()
        self.archive_browser_list.currentItemChanged.connect(self.on_archive_selected)
        browser_layout.addWidget(self.archive_browser_list, 1)

        browser_refresh_btn = QPushButton("Refresh List")
        browser_refresh_btn.clicked.connect(self.refresh_archive_browser)
        browser_layout.addWidget(browser_refresh_btn)

        right_column.addWidget(browser_box, 1)

        detail_box = QGroupBox("Selected Archive")
        detail_layout = QVBoxLayout(detail_box)
        self.archive_detail_view = QTextEdit()
        self.archive_detail_view.setReadOnly(True)
        self.archive_detail_view.setPlaceholderText("Select an archive on the left to view it here.")
        detail_layout.addWidget(self.archive_detail_view)
        right_column.addWidget(detail_box, 1)

        outer_layout.addLayout(right_column, 2)

        self.refresh_archive_browser()
        return page

def _parse_archive_summary(self, path: Path) -> dict:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = ""

        def extract(pattern: str) -> str:
            match = re.search(pattern, text, re.MULTILINE)
            return match.group(1).strip() if match else "Unknown"

            return {
            "id": path.stem,
            "location": extract(r"^Location\s+(.+)$"),
            "real_date": extract(r"Real Date:\s*(.+)"),
            "events": extract(r"Marker Events:\s*(\d+)"),
            "text": text,
            "search_blob": text.lower(),
            }

def refresh_archive_browser(self) -> None:
        self.archive_browser_list.clear()
        if not self.session_archive_folder.exists():
            return
        files = sorted(self.session_archive_folder.glob("ST-*.md"), reverse=True)
        for path in files:
            summary = self._parse_archive_summary(path)
            label = f"{summary['id']}  —  {summary['real_date']}  —  {summary['location']}  ({summary['events']} events)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, summary)
            self.archive_browser_list.addItem(item)
        self.filter_archive_browser()

def filter_archive_browser(self) -> None:
        query = self.archive_search_edit.text().strip().lower()
        for i in range(self.archive_browser_list.count()):
            item = self.archive_browser_list.item(i)
            summary = item.data(Qt.ItemDataRole.UserRole)
            matches = not query or query in summary["search_blob"] or query in summary["id"].lower()
            item.setHidden(not matches)

def on_archive_selected(self, current, previous) -> None:
        if current is None:
            return
        summary = current.data(Qt.ItemDataRole.UserRole)
        self.archive_detail_view.setPlainText(summary["text"])


def archive_current_run(self):
        self.refresh_archive_log()  # pull fresh data from disk rather than archive a stale view

        marker_log = self.marker_log_view.toPlainText()
        boss_log = self.boss_log_view.toPlainText()
        notes = self.session_notes_edit.toPlainText().strip() or "No notes recorded."

        self.session_archive_folder.mkdir(parents=True, exist_ok=True)
        archive_id = self.get_next_archive_number()

        # --- Pull the shared expedition fields straight from Broadcast Desk ---
        location = self._broadcast_location_text() or "Unspecified"
        expedition = self.broadcast_focus_combo.currentText() or "Unspecified"
        objective = self.broadcast_goal_edit.text().strip() or "Unspecified"
        team = self.broadcast_team_edit.text().strip() or "Unspecified"

        # --- Derive stats from the marker log itself, rather than tracking them separately ---
        marker_lines = [line for line in marker_log.splitlines() if line.strip()]
        marker_event_count = len(marker_lines)
        bosses_cleared_count = sum(1 for line in marker_lines if "Boss Clear" in line)
        incident_lines = [line for line in marker_lines if "Incident" in line]
        achievement_lines = [line for line in marker_lines if "Achievement" in line]

        elapsed_time = "Unknown"
        current_status = "No Events Yet"
        if marker_lines:
            last_line = marker_lines[-1]
            stream_match = re.search(r"Stream:\s*([\d:]+|not streaming)", last_line)
            if stream_match:
                stream_value = stream_match.group(1)
                if stream_value == "not streaming":
                    elapsed_time = "Not streaming"
                    current_status = "Not Streaming"
                else:
                    parts = stream_value.split(":")
                    if len(parts) == 3:
                        hours, minutes, _seconds = (int(p) for p in parts)
                        elapsed_time = (f"{hours}h {minutes}m" if hours else f"{minutes}m")
                    else:
                        elapsed_time = stream_value
                    current_status = "Expedition Active"

        real_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        tamriel_date = get_tamriel_date()

        divider = "─" * 24
        section_divider = "-" * 50

        summary = "\n".join([
            "CURRENT RUN",
            f"Archive ID   {archive_id}",
            f"Location     {location}",
            f"Expedition   {expedition}",
            f"Objective    {objective}",
            f"Team         {team}",
            divider,
            f"Marker Events: {marker_event_count}   Bosses Cleared: {bosses_cleared_count}   "
            f"Incidents: {len(incident_lines)}   Achievements: {len(achievement_lines)}   "
            f"Elapsed Time: {elapsed_time}",
            divider,
            f"Current Status  {'✓' if current_status == 'Expedition Active' else '•'} {current_status}",
            f"Real Date: {real_date}",
            f"Tamriel Date: {tamriel_date}",
        ])

        archive_text = "\n".join([
            summary,
            section_divider,
            "## Marker Log",
            "",
            marker_log or "No marker events recorded.",
            section_divider,
            "## Boss Log",
            "",
            boss_log or "No bosses cleared this session.",
            section_divider,
            "## Incident Reports",
            "",
            "\n".join(incident_lines) if incident_lines else "No incidents recorded.",
            section_divider,
            "## Notes",
            "",
            notes,
            "",
        ])

        filename = self.session_archive_folder / f"{archive_id}.md"
        filename.write_text(archive_text, encoding="utf-8")
        self.status_label.setText(f"Archive saved to {filename}")

def get_next_archive_number(self):
        self.session_archive_folder.mkdir(parents=True, exist_ok=True)
        highest = 0
        for file in self.session_archive_folder.glob("ST-*.md"):
            match = re.match(r"ST-(\d+)\.md", file.name)
            if match:
                highest = max(highest, int(match.group(1)))
        return f"ST-{highest + 1:06d}"

def refresh_archive_log(self) -> None:
        try:
            if self.marker_log_path.exists():
                self.marker_log_view.setPlainText(self.marker_log_path.read_text(encoding="utf-8"))
            else:
                self.marker_log_view.setPlainText("(No MarkerLog.md yet - nothing has been logged this session.)")
            self.marker_log_view.verticalScrollBar().setValue(self.marker_log_view.verticalScrollBar().maximum())
        except OSError as exc:
            self.marker_log_view.setPlainText(f"Couldn't read Marker Log: {exc}")

        try:
            if self.boss_log_path.exists():
                self.boss_log_view.setPlainText(self.boss_log_path.read_text(encoding="utf-8"))
            else:
                self.boss_log_view.setPlainText("(No BossLog.md yet - no bosses cleared this session.)")
            self.boss_log_view.verticalScrollBar().setValue(self.boss_log_view.verticalScrollBar().maximum())
        except OSError as exc:
            self.boss_log_view.setPlainText(f"Couldn't read Boss Log: {exc}")

def clear_archive(self):
        """Clear the current archive display."""
        self.marker_log_view.clear()
        self.boss_log_view.clear()
        self.status_label.setText("Archive display cleared.")


