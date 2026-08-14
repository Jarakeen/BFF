# ui/achievement_page.py
from __future__ import annotations


import json
import random
from datetime import datetime
from pathlib import Path
import re



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



def _build_achievement_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self.achievement_run_id_label = QLabel("AR-—")
        self.achievement_run_id_label.setObjectName("achievementRunId")
        id_row = QHBoxLayout()
        id_row.addStretch(1)
        id_row.addWidget(QLabel("RUN ID"))
        id_row.addWidget(self.achievement_run_id_label)
        layout.addLayout(id_row)

        details = QGroupBox("Run Details")
        detail_grid = QGridLayout(details)
        self.achievement_date_edit = QLineEdit(datetime.now().strftime("%m / %d / %Y"))
        self.achievement_content_combo = QComboBox()
        self.achievement_content_combo.setEditable(True)
        self.achievement_content_combo.addItems(self._eso_run_content())
        self.achievement_group_size = QSpinBox()
        self.achievement_group_size.setRange(1, 24)
        self.achievement_group_size.setValue(4)
        detail_grid.addWidget(QLabel("DATE"), 0, 0)
        detail_grid.addWidget(QLabel("DUNGEON / TRIAL"), 0, 1)
        detail_grid.addWidget(QLabel("GROUP SIZE"), 0, 2)
        detail_grid.addWidget(self.achievement_date_edit, 1, 0)
        detail_grid.addWidget(self.achievement_content_combo, 1, 1)
        detail_grid.addWidget(self.achievement_group_size, 1, 2)
        self.achievement_normal_cb = QCheckBox("Normal")
        self.achievement_veteran_cb = QCheckBox("Veteran")
        self.achievement_hard_mode_cb = QCheckBox("Hard Mode")
        self.achievement_perfecta_cb = QCheckBox("Perfecta")
        self.achievement_veteran_cb.setChecked(True)
        difficulty_row = QHBoxLayout()
        for checkbox in (self.achievement_normal_cb, self.achievement_veteran_cb, self.achievement_hard_mode_cb, self.achievement_perfecta_cb):
            difficulty_row.addWidget(checkbox)
        detail_grid.addWidget(QLabel("DIFFICULTY"), 2, 0)
        detail_grid.addLayout(difficulty_row, 3, 0, 1, 2)
        self.achievement_full_clear_cb = QCheckBox("Full Clear")
        self.achievement_only_cb = QCheckBox("Achievements Only")
        self.achievement_speed_run_cb = QCheckBox("Speed Run")
        self.achievement_teaching_cb = QCheckBox("Teaching Run")
        run_type_row = QHBoxLayout()
        for checkbox in (self.achievement_full_clear_cb, self.achievement_only_cb, self.achievement_speed_run_cb, self.achievement_teaching_cb):
            run_type_row.addWidget(checkbox)
        detail_grid.addWidget(QLabel("RUN TYPE"), 2, 2)
        detail_grid.addLayout(run_type_row, 3, 2)
        layout.addWidget(details)

        body = QHBoxLayout()
        targets_box = QGroupBox("Achievements Targeted")
        targets_grid = QGridLayout(targets_box)
        targets_grid.addWidget(QLabel("ACHIEVEMENT"), 0, 0)
        targets_grid.addWidget(QLabel("IN PROGRESS"), 0, 1)
        targets_grid.addWidget(QLabel("COMPLETE"), 0, 2)
        self.achievement_target_edits: list[QLineEdit] = []
        self.achievement_progress_cbs: list[QCheckBox] = []
        self.achievement_complete_cbs: list[QCheckBox] = []
        for row in range(5):
            target = QLineEdit()
            target.setPlaceholderText(f"Achievement {row + 1}")
            in_progress = QCheckBox()
            complete = QCheckBox()
            self.achievement_target_edits.append(target)
            self.achievement_progress_cbs.append(in_progress)
            self.achievement_complete_cbs.append(complete)
            targets_grid.addWidget(target, row + 1, 0)
            targets_grid.addWidget(in_progress, row + 1, 1, Qt.AlignmentFlag.AlignCenter)
            targets_grid.addWidget(complete, row + 1, 2, Qt.AlignmentFlag.AlignCenter)
        body.addWidget(targets_box, 1)

        notes_column = QVBoxLayout()
        self.achievement_notes = QTextEdit()
        self.achievement_notes.setPlaceholderText("Clean pulls, boss notes, and key moments.")
        self.achievement_lessons = QTextEdit()
        self.achievement_lessons.setPlaceholderText("Lessons learned and improvements for next time.")
        self.achievement_next_steps = QTextEdit()
        self.achievement_next_steps.setPlaceholderText("What should the crew try next?")
        notes_column.addWidget(self._make_section("Run Notes / Key Moments", self.achievement_notes))
        notes_column.addWidget(self._make_section("Lessons Learned / Improvements", self.achievement_lessons))
        notes_column.addWidget(self._make_section("What's Next?", self.achievement_next_steps))
        body.addLayout(notes_column, 1)
        layout.addLayout(body)

        outcome = QGroupBox("Run Result")
        outcome_row = QHBoxLayout(outcome)
        self.achievement_success_cb = QCheckBox("Success!")
        self.achievement_partial_cb = QCheckBox("Partial Success")
        self.achievement_not_today_cb = QCheckBox("Not Today")
        self.achievement_time_edit = QLineEdit()
        self.achievement_time_edit.setPlaceholderText("00 : 00 : 00")
        for widget in (self.achievement_success_cb, self.achievement_partial_cb, self.achievement_not_today_cb):
            outcome_row.addWidget(widget)
        outcome_row.addStretch(1)
        outcome_row.addWidget(QLabel("FINAL SCORE / TIME"))
        outcome_row.addWidget(self.achievement_time_edit)
        layout.addWidget(outcome)

        actions = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        obs_btn = QPushButton("Save to OBS")
        draft_btn = QPushButton("Save Draft")
        load_btn = QPushButton("Load Draft")
        archive_btn = QPushButton("Save to Archive")
        clear_btn.clicked.connect(self.clear_achievement_run)
        obs_btn.clicked.connect(self.save_broadcast_to_obs)
        draft_btn.clicked.connect(self.save_achievement_draft)
        load_btn.clicked.connect(self.load_achievement_draft)
        archive_btn.clicked.connect(self.archive_achievement_run)
        actions.addWidget(clear_btn)
        actions.addWidget(obs_btn)
        actions.addWidget(load_btn)
        actions.addStretch(1)
        actions.addWidget(draft_btn)
        actions.addWidget(archive_btn)
        layout.addLayout(actions)
        return page

def _achievement_payload(self) -> dict:
        targets = []
        for target, in_progress, complete in zip(
            self.achievement_target_edits,
            self.achievement_progress_cbs,
            self.achievement_complete_cbs,
        ):
            if target.text().strip() or in_progress.isChecked() or complete.isChecked():
                targets.append({
                    "name": target.text().strip(),
                    "in_progress": in_progress.isChecked(),
                    "complete": complete.isChecked(),
                })
        return {
            "run_id": self.achievement_run_id_label.text(),
            "date": self.achievement_date_edit.text().strip(),
            "content": self.achievement_content_combo.currentText().strip(),
            "group_size": self.achievement_group_size.value(),
            "difficulty": [name for name, box in (
                ("Normal", self.achievement_normal_cb), ("Veteran", self.achievement_veteran_cb),
                ("Hard Mode", self.achievement_hard_mode_cb), ("Perfecta", self.achievement_perfecta_cb),
            ) if box.isChecked()],
            "run_type": [name for name, box in (
                ("Full Clear", self.achievement_full_clear_cb), ("Achievements Only", self.achievement_only_cb),
                ("Speed Run", self.achievement_speed_run_cb), ("Teaching Run", self.achievement_teaching_cb),
            ) if box.isChecked()],
            "targets": targets,
            "notes": self.achievement_notes.toPlainText().strip(),
            "lessons": self.achievement_lessons.toPlainText().strip(),
            "next_steps": self.achievement_next_steps.toPlainText().strip(),
            "result": next((name for name, box in (
                ("Success", self.achievement_success_cb), ("Partial Success", self.achievement_partial_cb),
                ("Not Today", self.achievement_not_today_cb),
            ) if box.isChecked()), ""),
            "final_time": self.achievement_time_edit.text().strip(),
        }

def _apply_achievement_payload(self, data: dict) -> None:
        self.achievement_run_id_label.setText(data.get("run_id") or "AR-—")
        self.achievement_date_edit.setText(data.get("date", datetime.now().strftime("%m / %d / %Y")))
        self.achievement_content_combo.setCurrentText(data.get("content", ""))
        self.achievement_group_size.setValue(int(data.get("group_size", 4)))
        for name, box in (("Normal", self.achievement_normal_cb), ("Veteran", self.achievement_veteran_cb), ("Hard Mode", self.achievement_hard_mode_cb), ("Perfecta", self.achievement_perfecta_cb)):
            box.setChecked(name in data.get("difficulty", []))
        for name, box in (("Full Clear", self.achievement_full_clear_cb), ("Achievements Only", self.achievement_only_cb), ("Speed Run", self.achievement_speed_run_cb), ("Teaching Run", self.achievement_teaching_cb)):
            box.setChecked(name in data.get("run_type", []))
        for index, target in enumerate(data.get("targets", [])[:5]):
            self.achievement_target_edits[index].setText(target.get("name", ""))
            self.achievement_progress_cbs[index].setChecked(bool(target.get("in_progress")))
            self.achievement_complete_cbs[index].setChecked(bool(target.get("complete")))
        self.achievement_notes.setPlainText(data.get("notes", ""))
        self.achievement_lessons.setPlainText(data.get("lessons", ""))
        self.achievement_next_steps.setPlainText(data.get("next_steps", ""))
        result = data.get("result", "")
        self.achievement_success_cb.setChecked(result == "Success")
        self.achievement_partial_cb.setChecked(result == "Partial Success")
        self.achievement_not_today_cb.setChecked(result == "Not Today")
        self.achievement_time_edit.setText(data.get("final_time", ""))

def clear_achievement_run(self) -> None:
        self._apply_achievement_payload({})
        for target, in_progress, complete in zip(self.achievement_target_edits, self.achievement_progress_cbs, self.achievement_complete_cbs):
            target.clear()
            in_progress.setChecked(False)
            complete.setChecked(False)
        self.status_label.setText("Achievement run form cleared")

def save_achievement_to_obs(self) -> None:
        try:
            payload = self._achievement_payload()
            self.current_achievement_run_path.parent.mkdir(parents=True, exist_ok=True)
            self.current_achievement_run_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=4), encoding="utf-8"
            )
            self.status_label.setText(
                "Saved to OBS (CurrentAchievementRun.json) - matching OBS text sources not wired up yet, see AR_ note"
            )
        except OSError as exc:
            self.status_label.setText(f"Save to OBS failed: {exc}")

def save_achievement_draft(self) -> None:
        try:
            self.achievement_draft_path.parent.mkdir(parents=True, exist_ok=True)
            self.achievement_draft_path.write_text(json.dumps(self._achievement_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_label.setText("Achievement run draft saved")
        except OSError as exc:
            self.status_label.setText(f"Achievement draft failed: {exc}")

def load_achievement_draft(self) -> None:
        try:
            data = json.loads(self.achievement_draft_path.read_text(encoding="utf-8"))
            self.clear_achievement_run()
            self._apply_achievement_payload(data)
            self.status_label.setText("Achievement run draft loaded")
        except (OSError, json.JSONDecodeError) as exc:
            self.status_label.setText(f"Achievement draft unavailable: {exc}")

def archive_achievement_run(self) -> None:
        data = self._achievement_payload()
        try:
            def build_lines(run_id: str, _number: int) -> list[str]:
                target_lines = [f"- {'✓' if target['complete'] else '•'} {target['name'] or 'Untitled achievement'}" for target in data["targets"]]
                return [
                    f"# Achievement Run {run_id}", "", f"- Date: {data['date']}",
                    f"- Dungeon / Trial: {data['content'] or 'Unspecified'}", f"- Group Size: {data['group_size']}",
                    f"- Difficulty: {', '.join(data['difficulty']) or 'Unspecified'}", f"- Run Type: {', '.join(data['run_type']) or 'Unspecified'}", "",
                    "## Achievements Targeted", *(target_lines or ["- None listed"]), "",
                    "## Run Notes / Key Moments", data["notes"] or "No notes recorded.", "",
                    "## Lessons Learned / Improvements", data["lessons"] or "No lessons recorded.", "",
                    "## What's Next?", data["next_steps"] or "No follow-up recorded.", "",
                    f"- Result: {data['result'] or 'Not recorded'}", f"- Final Score / Time: {data['final_time'] or 'Not recorded'}",
                ]

            run_id, archive_path = self.archive_service.file_form("AR", build_lines)
            self.achievement_run_id_label.setText(run_id)
            self.save_achievement_draft()
            self.stream_event_service.fire_event(
                log_label=f"Achievement Run filed: {run_id} | {data['content'] or 'Unspecified'}"
            )
            self.status_label.setText(f"Achievement run archived: {archive_path.name}")
        except OSError as exc:
            self.status_label.setText(f"Achievement archive failed: {exc}")
