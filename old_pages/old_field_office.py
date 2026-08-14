# ui/field_office.py
from __future__ import annotations


import json
import random
from datetime import datetime
from pathlib import Path
import re
from models.expedition_model import ExpeditionModel, StatusFlags


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


def _build_expedition_page(self) -> QWidget:
        page = QWidget()

    # Overall page layout (top content + bottom buttons)
        root_layout = QVBoxLayout(page)

    # Split page left/right
        content_layout = QHBoxLayout()
        root_layout.addLayout(content_layout, 1)

        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()

        content_layout.addLayout(left_panel, 1)
        content_layout.addLayout(right_panel, 1)

        #
        # Create status checkboxes FIRST
        #
        self._build_status_checkboxes()

        #
        # LEFT SIDE
        #

        clipboard_label = QLabel("CLIPBOARD")
        left_panel.addWidget(clipboard_label)
        left_panel.addWidget(self._make_section("Assignment", self.assignment))
        left_panel.addWidget(self._make_clipboard_status_panel())


        field_note_label = QLabel("FIELD NOTE")
        left_panel.addWidget(field_note_label)
        left_panel.addWidget(self._make_section("Observation", self.observation))
        left_panel.addWidget(self._make_section("Context", self.context))
        left_panel.addWidget(
        self._make_section(
        "Recommendations for Future Adventurers",
        self.next_steps,
        )
        )
        left_panel.addWidget(self._make_fieldnote_status_panel())

        left_panel.addStretch()

        #
        # RIGHT SIDE
        #

        notes_label = QLabel("FIELD NOTES")
        right_panel.addWidget(notes_label)

        self.field_notes_edit = QTextEdit()
        self.field_notes_edit.setPlaceholderText(
        "Record observations, reminders, or discoveries..."
        )
        right_panel.addWidget(self.field_notes_edit, 1)

        save_note_btn = QPushButton("Save to Archive")
        save_note_btn.clicked.connect(self.new_field_note)
        right_panel.addWidget(save_note_btn)

        #
        # Bottom Action Buttons
        #

        actions = QHBoxLayout()

        self.clear_btn = QPushButton("Clear")
        self.save_btn = QPushButton("Save to OBS")
        self.new_note_btn = QPushButton("Save to Archive")
        self.load_btn = QPushButton("Load Expedition")
        self.incident_btn = QPushButton("Open Incident Report")

        self.clear_btn.clicked.connect(self.clear_expedition)
        self.load_btn.clicked.connect(self.load_expedition)
        self.save_btn.clicked.connect(self.save_expedition)
        self.new_note_btn.clicked.connect(self.new_field_note)
        self.incident_btn.clicked.connect(lambda: self._select_page(4))

        actions.addWidget(self.clear_btn)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.new_note_btn)
        actions.addWidget(self.load_btn)
        actions.addWidget(self.incident_btn)

        root_layout.addLayout(actions)

        return page

def new_field_note(self) -> None:
        self.status_label.setText("Updating field note counter...")
        try:
            counter_path = self.field_note_counter_path
            archive_folder = self.archive_path
            archive_folder.mkdir(parents=True, exist_ok=True)

            if not counter_path.exists():
                counter_path.parent.mkdir(parents=True, exist_ok=True)
                counter_path.write_text("0", encoding="utf-8")

            current_value = int(counter_path.read_text(encoding="utf-8").strip().strip('"').strip("'"))
            new_value = current_value + 1
            counter_path.write_text(str(new_value), encoding="utf-8")

            note_path = archive_folder / f"FieldNote_{new_value:04d}.md"
            note_text = "\n".join(
                [
                    "# Field Note",
                    "",
                    f"- Expedition: {self._broadcast_location_text() or 'Unknown'}",
                    f"- Objective: {self.broadcast_goal_edit.text().strip() or 'Unknown'}",
                    f"- Weather: {self.broadcast_weather.currentText() or 'Unknown'}",
                    f"- Coffee: {self.broadcast_coffee.currentText() or 'Unknown'}",
                    f"- Note: {self._current_field_note_text()}",
                    f"- Created: {datetime.now().isoformat(timespec='seconds')}",
                    "",
                ]
            )
            note_path.write_text(note_text, encoding="utf-8")
            self.status_label.setText(f"Field note counter: {new_value} | Note: {note_path.name}")
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Counter update failed: {exc}")
 
       
def _collect_model(self) -> ExpeditionModel:
    status = StatusFlags(
            Observe=self.observe_cb.isChecked(),
            Document=self.document_cb.isChecked(),
            Learn=self.learn_cb.isChecked(),
            ShareTheLesson=self.share_cb.isChecked(),
            InProgress=self.in_progress_cb.isChecked(),
            Complete=self.complete_cb.isChecked(),
            UnderReview=self.under_review_cb.isChecked(),
    )

    return ExpeditionModel(
                    Expedition=self._broadcast_location_text(),
                    Difficulty=self._current_difficulty_text(),
                    Objective=self.broadcast_goal_edit.text().strip(),
                    Weather=self.broadcast_weather.currentText(),
                    Coffee=COFFEE_SOURCE_MAP.get(self.broadcast_coffee.currentText(), self.broadcast_coffee.currentText()),
                    CoffeeLevel=self.broadcast_coffee_level.text(),
                    Engineering=self.broadcast_engineering.currentText(),
                    Incidents=self.broadcast_incidents.text(),
                    Assignment=self.assignment.toPlainText(),
                    Observation=self.observation.toPlainText(),
                    Context=self.context.toPlainText(),
                    NextSteps=self.next_steps.toPlainText(),
                    Status=status,
        )


def _apply_model(self, model: ExpeditionModel) -> None:
        # Expedition/Difficulty/Objective/Weather/Coffee/CoffeeLevel/Engineering/
        # Incidents now live on Broadcast Desk (the shared source) - loading a
        # saved snapshot writes back there, and Field Office's read-only
        # summary picks it up via refresh_top_bar_summary().
        if self.broadcast_location_stack.currentWidget() is self.broadcast_location_combo:
            self.broadcast_location_combo.setCurrentText(model.Expedition)
        else:
            self.broadcast_location_edit.setText(model.Expedition)
        self._set_difficulty_text(model.Difficulty)
        self.broadcast_goal_edit.setText(model.Objective)
        current_weather = model.Weather
        if current_weather in WEATHER_SOURCE_MAP:
            self.broadcast_weather.setCurrentText(current_weather)
        elif self.broadcast_weather.count() > 0:
            self.broadcast_weather.setCurrentIndex(0)
        current_coffee = model.Coffee
        for label, mapped_value in COFFEE_SOURCE_MAP.items():
            if mapped_value == current_coffee:
                self.broadcast_coffee.setCurrentText(label)
                break
        else:
            if self.broadcast_coffee.count() > 0:
                self.broadcast_coffee.setCurrentIndex(0)
        self.broadcast_coffee_level.setText(model.CoffeeLevel)
        self.broadcast_engineering.setCurrentText(model.Engineering)
        self.broadcast_incidents.setText(model.Incidents)
        self.assignment.setPlainText(model.Assignment)
        self.observation.setPlainText(model.Observation)
        self.context.setPlainText(model.Context)
        self.next_steps.setPlainText(model.NextSteps)
        self.observe_cb.setChecked(model.Status.Observe)
        self.document_cb.setChecked(model.Status.Document)
        self.learn_cb.setChecked(model.Status.Learn)
        self.share_cb.setChecked(model.Status.ShareTheLesson)
        self.in_progress_cb.setChecked(model.Status.InProgress)
        self.complete_cb.setChecked(model.Status.Complete)
        self.under_review_cb.setChecked(model.Status.UnderReview)
        self.refresh_top_bar_summary()

def _make_clipboard_status_panel(self) -> QGroupBox:
            box = QGroupBox("Status")
            layout = QVBoxLayout(box)
            layout.addWidget(self.observe_cb)
            layout.addWidget(self.document_cb)
            layout.addWidget(self.learn_cb)
            layout.addWidget(self.share_cb)
            return box    

@property
def assignment(self) -> QTextEdit:
            if not hasattr(self, "_assignment"):
                self._assignment = QTextEdit()
                self._assignment.setPlaceholderText("Assignment")
            return self._assignment