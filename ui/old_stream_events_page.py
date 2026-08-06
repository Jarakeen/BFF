# ui/stream_events.py
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



def _build_stream_events_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        boss_row = QHBoxLayout()
        boss_row.addWidget(QLabel("Current Boss:"))
        self.current_boss_edit = QLineEdit()
        boss_row.addWidget(self.current_boss_edit)
        layout.addLayout(boss_row)

        counters_box = QGroupBox("This Stream")
        counters_layout = QHBoxLayout(counters_box)
        self.total_pulls_label = QLabel("Total Pulls: 0")
        self.boss_pulls_label = QLabel("Pulls on Boss: 0")
        self.boss_wipes_label = QLabel("Wipes on Boss: 0")
        counters_layout.addWidget(self.total_pulls_label)
        counters_layout.addWidget(self.boss_pulls_label)
        counters_layout.addWidget(self.boss_wipes_label)
        layout.addWidget(counters_box)

        pull_box = QGroupBox("Pull Starts")
        pull_layout = QHBoxLayout(pull_box)
        self.first_pull_cb = QCheckBox("First pull on this boss (marks a chapter)")
        pull_starts_btn = QPushButton("Pull Starts")
        pull_starts_btn.clicked.connect(self.on_pull_starts)
        ult_pull_btn = QPushButton("Ult Pull")
        ult_pull_btn.setMaximumWidth(80)
        ult_pull_btn.setToolTip("Marks a chapter for this pull only - does not touch pull/wipe counters")
        ult_pull_btn.clicked.connect(self.on_ult_pull)
        pull_layout.addWidget(self.first_pull_cb)
        pull_layout.addWidget(pull_starts_btn)
        pull_layout.addWidget(ult_pull_btn)
        layout.addWidget(pull_box)

        wipe_box = QGroupBox("Wipes")
        wipe_layout = QHBoxLayout(wipe_box)
        wipe_layout.addWidget(QLabel("Reached:"))
        self.wipe_percent_spin = QSpinBox()
        self.wipe_percent_spin.setRange(0, 100)
        self.wipe_percent_spin.setSuffix("%")
        wipe_layout.addWidget(self.wipe_percent_spin)
        self.rough_night_cb = QCheckBox("Rough night (skip narrator posts)")
        wipe_layout.addWidget(self.rough_night_cb)
        wipe_btn = QPushButton("Wipes")
        wipe_btn.clicked.connect(self.on_wipe)
        wipe_layout.addWidget(wipe_btn)
        layout.addWidget(wipe_box)

        boss_clear_btn = QPushButton("Boss Clears")
        boss_clear_btn.clicked.connect(self.on_boss_clear)
        layout.addWidget(boss_clear_btn)

        narrator_box = QGroupBox("Natural History Narrator")
        narrator_layout = QHBoxLayout(narrator_box)
        narrator_buttons = [
            ("General Observations", "General"),
            ("Healers", "Healers"),
            ("Tanks", "Tanks"),
            ("DPS", "DPS"),
            ("🤣 Funny Moments", "FunnyMoments"),
            ("📖 Progression", "Progression"),
        ]
        for label, category in narrator_buttons:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked=False, c=category: self.post_narrator_note(c))
            narrator_layout.addWidget(btn)
        layout.addWidget(narrator_box)

        scene_box = QGroupBox("Scene Switches")
        scene_layout = QHBoxLayout(scene_box)
        brb_btn = QPushButton("☕ BRB")
        brb_btn.clicked.connect(self.on_brb)
        end_stream_btn = QPushButton("🌙 End of Stream")
        end_stream_btn.clicked.connect(self.on_end_of_stream)
        scene_layout.addWidget(brb_btn)
        scene_layout.addWidget(end_stream_btn)
        layout.addWidget(scene_box)

        reset_btn = QPushButton("Reset Pull/Wipe Counters (new stream)")
        reset_btn.clicked.connect(self.reset_stream_session)
        layout.addWidget(reset_btn)

        layout.addStretch(1)
        return page


def _load_stream_session(self) -> None:
        session = self.stream_event_service.load_session()
        self.current_boss_edit.setText(session.get("CurrentBoss", ""))
        self._refresh_session_labels(session)

def _refresh_session_labels(self, session: dict) -> None:
        self.total_pulls_label.setText(f"Total Pulls: {session.get('TotalPulls', 0)}")
        self.boss_pulls_label.setText(f"Pulls on Boss: {session.get('BossPulls', 0)}")
        self.boss_wipes_label.setText(f"Wipes on Boss: {session.get('BossWipes', 0)}")

def reset_stream_session(self) -> None:
        self.current_boss_edit.clear()
        session = {"TotalPulls": 0, "CurrentBoss": "", "BossPulls": 0, "BossWipes": 0}
        self.stream_event_service.save_session(session)
        self._refresh_session_labels(session)
        self.status_label.setText("Stream session counters reset")

def on_pull_starts(self) -> None:
        session = self.stream_event_service.load_session()
        boss = self.current_boss_edit.text()
        if session.get("CurrentBoss", "") != boss:
            session["BossPulls"] = 0
            session["BossWipes"] = 0
            session["CurrentBoss"] = boss
        session["TotalPulls"] = session.get("TotalPulls", 0) + 1
        session["BossPulls"] = session.get("BossPulls", 0) + 1
        self.stream_event_service.save_session(session)
        self._refresh_session_labels(session)

        boss_label = boss or "Unnamed Boss"
        pull_summary = f"Pull Starts | Boss: {boss_label} | Pull #{session['BossPulls']} (Total: {session['TotalPulls']})"

        if self.first_pull_cb.isChecked():
            self.stream_event_service.fire_event(chapter_label=f"First Pull: {boss_label}")
            self.first_pull_cb.setChecked(False)
            self.status_label.setText(f"Pull started - chapter marked (First Pull: {boss})")
        else:
            self.stream_event_service.fire_event(log_label=pull_summary)
            self.status_label.setText(f"Pull #{session['BossPulls']} started on {boss_label}")

def on_ult_pull(self) -> None:
        boss = self.current_boss_edit.text()
        self.stream_event_service.fire_event(chapter_label=f"Ult Pull: {boss or 'Unnamed Boss'}")
        self.status_label.setText(f"Ult pull marked ({boss}) - counters untouched")

def _flash_widget(self, widget, color: str = "#c9a227", duration_ms: int = 450) -> None:
        original_style = widget.styleSheet()
        widget.setStyleSheet(f"background-color: {color}; font-weight: bold;")
        QTimer.singleShot(duration_ms, lambda: widget.setStyleSheet(original_style))

def on_wipe(self) -> None:
        session = self.stream_event_service.load_session()
        boss = self.current_boss_edit.text()
        session["BossWipes"] = session.get("BossWipes", 0) + 1
        self.stream_event_service.save_session(session)
        self._refresh_session_labels(session)
        self._flash_widget(self.boss_wipes_label)

        percent = self.wipe_percent_spin.value()
        boss_label = boss or "Unnamed Boss"
        wipe_summary = (
            f"Wipe | Boss: {boss_label} | Wipe #{session['BossWipes']} on Pull #{session.get('BossPulls', 0)} "
            f"| Reached: {percent}%"
        )
        narrator_text = ""
        if not self.rough_night_cb.isChecked():
            narrator_text = self.narrator_service.pick("Wipes")
        self.stream_event_service.fire_event(narrator_text=narrator_text, log_label=wipe_summary)
        self.status_label.setText(f"✅ Wipe #{session['BossWipes']} recorded on {boss_label} at {percent}%")

def on_boss_clear(self) -> None:
        session = self.stream_event_service.load_session()
        boss = self.current_boss_edit.text()
        pulls = session.get("BossPulls", 0)
        wipes = session.get("BossWipes", 0)
        self.stream_event_service.append_boss_log(boss, pulls, wipes)

        boss_label = boss or "Unnamed Boss"
        narrator_text = self.narrator_service.pick("BossClear")
        self.stream_event_service.fire_event(
            chapter_label=f"Boss Clear: {boss_label} (Pulls: {pulls}, Wipes: {wipes})",
            narrator_text=narrator_text,
        )

        session["BossPulls"] = 0
        session["BossWipes"] = 0
        self.stream_event_service.save_session(session)
        self._refresh_session_labels(session)
        self.status_label.setText(f"Boss clear logged: {boss}")

def post_narrator_note(self, category: str) -> None:
        narrator_text = self.narrator_service.pick(category)
        self.stream_event_service.fire_event(narrator_text=narrator_text)
        self.status_label.setText(f"Posted a {category} note")

def on_brb(self) -> None:
        narrator_text = self.narrator_service.pick("BRB")
        self.stream_event_service.fire_event(chapter_label="BRB", narrator_text=narrator_text)
        self.obs_websocket_service.switch_scene(self.brb_scene_name)
        self.status_label.setText("BRB - chapter marked; switching OBS scene")

def on_end_of_stream(self) -> None:
        narrator_text = self.narrator_service.pick("EndOfStream")
        self.stream_event_service.fire_event(narrator_text=narrator_text)
        self.obs_websocket_service.switch_scene(self.end_of_stream_scene_name)
        self.status_label.setText("End of stream - switching OBS scene")