from __future__ import annotations

"""Independent UI stopwatch and persistent notepad support.

This compatibility layer keeps presentation/state fixes isolated from the combat
engine. User-facing stopwatches own their own QTimer and elapsed state, while
notepad-style cards get separate editable text buffers persisted by unique keys.
"""

import json
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton

from engine.config import get_data_dir

_INSTALLED = False
_STATE_FILE = get_data_dir() / "workspace_notes.json"


_DEFAULT_NOTES = {
    "mechanics.quick_notes": (
        "Portal control is critical.\n"
        "Heavy damage in execute.\n"
        "Call mechanics early.\n"
        "Watch positioning."
    ),
    "mechanics.callouts": (
        "Mechanic incoming!\n"
        "Move / stack / spread.\n"
        "Execute callout.\n"
        "Custom raid-lead callouts."
    ),
    "mechanics.my_notes": "",
    "mechanics.reminders": (
        "Important threshold reminders\n"
        "Positioning notes\n"
        "Tank/healer warnings\n"
        "Execute reminders"
    ),
    "mechanics.history": (
        "Pull history\n"
        "Best attempt\n"
        "Repeat failure points\n"
        "Successful adjustments"
    ),
    "mechanics.notes_tab": "",
    "overview.raid_notes": (
        "Watch portals on the east side\n"
        "Don't cleave the shades\n"
        "Save ults for execute\n"
        "Call inc's early\n"
        "Breathe. We got this."
    ),
}


def _load_state() -> dict[str, str]:
    try:
        payload = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(value) for key, value in payload.items() if isinstance(value, str)}


def _save_value(key: str, value: str) -> None:
    payload = _load_state()
    payload[key] = value
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _note_editor(key: str, *, minimum_height: int = 80, placeholder: str = "Write notes here…") -> QPlainTextEdit:
    editor = QPlainTextEdit()
    editor.setProperty("parchment", True)
    editor.setProperty("independentNotepad", True)
    editor.setMinimumHeight(minimum_height)
    editor.setPlaceholderText(placeholder)
    saved = _load_state().get(key, _DEFAULT_NOTES.get(key, ""))
    editor.setPlainText(saved)
    editor.textChanged.connect(lambda e=editor, k=key: _save_value(k, e.toPlainText()))
    return editor


def _clear_card(card) -> None:
    card.clear()


def _find_card(root, title: str):
    from ui.components.foundry_card import FoundryCard

    for card in root.findChildren(FoundryCard):
        if getattr(card, "title_label", None) is not None and card.title_label.text() == title:
            return card
    return None


def _install_mechanics() -> None:
    from ui import mechanics_page

    original_build_ui = mechanics_page.MechanicsPage._build_ui

    def build_ui_with_independent_tools(self):
        original_build_ui(self)

        # Each note surface gets its own editor and persistence key.
        note_specs = {
            "Quick Notes": ("mechanics.quick_notes", 92),
            "Important Call Outs": ("mechanics.callouts", 92),
            "My Notes": ("mechanics.my_notes", 180),
            "Key Reminders": ("mechanics.reminders", 108),
            "Historical Notes": ("mechanics.history", 108),
        }
        for title, (key, height) in note_specs.items():
            card = _find_card(self, title)
            if card is None:
                continue
            _clear_card(card)
            editor = _note_editor(key, minimum_height=height)
            editor.setObjectName(key.replace(".", "_"))
            card.addWidget(editor)
            if title == "My Notes":
                self.my_notes_editor = editor

        # The NOTES tab already contains an editor, but it previously had no
        # independent persistence. Replace its contents deterministically.
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index) != "NOTES":
                continue
            tab = self.tabs.widget(index)
            layout = tab.layout()
            if layout is None:
                break
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self.notes_tab_editor = _note_editor(
                "mechanics.notes_tab",
                minimum_height=240,
                placeholder="Encounter notes…",
            )
            layout.addWidget(self.notes_tab_editor)
            break

        # Replace the decorative Encounter Timer controls with a real,
        # page-instance-owned stopwatch. No shared globals, no shared reset.
        timer_card = _find_card(self, "Encounter Timer")
        if timer_card is not None:
            _clear_card(timer_card)
            self.encounter_elapsed_seconds = 0
            self.encounter_timer_running = False

            self.encounter_timer_value = QLabel("00:00")
            self.encounter_timer_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.encounter_timer_value.setProperty("timerValue", True)
            timer_card.addWidget(self.encounter_timer_value)

            controls = QHBoxLayout()
            self.encounter_timer_start = QPushButton("Start")
            self.encounter_timer_reset = QPushButton("Reset")
            controls.addWidget(self.encounter_timer_start)
            controls.addWidget(self.encounter_timer_reset)
            timer_card.addLayout(controls)

            self.encounter_timer = QTimer(self)
            self.encounter_timer.setInterval(1000)

            def render_timer() -> None:
                minutes, seconds = divmod(int(self.encounter_elapsed_seconds), 60)
                hours, minutes = divmod(minutes, 60)
                if hours:
                    self.encounter_timer_value.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                else:
                    self.encounter_timer_value.setText(f"{minutes:02d}:{seconds:02d}")

            def tick_timer() -> None:
                self.encounter_elapsed_seconds += 1
                render_timer()

            def toggle_timer() -> None:
                if self.encounter_timer_running:
                    self.encounter_timer.stop()
                    self.encounter_timer_running = False
                    self.encounter_timer_start.setText("Start")
                else:
                    self.encounter_timer.start()
                    self.encounter_timer_running = True
                    self.encounter_timer_start.setText("Pause")

            def reset_timer() -> None:
                self.encounter_timer.stop()
                self.encounter_timer_running = False
                self.encounter_elapsed_seconds = 0
                self.encounter_timer_start.setText("Start")
                render_timer()

            self.encounter_timer.timeout.connect(tick_timer)
            self.encounter_timer_start.clicked.connect(toggle_timer)
            self.encounter_timer_reset.clicked.connect(reset_timer)

    mechanics_page.MechanicsPage._build_ui = build_ui_with_independent_tools


def _install_overview_raid_notes() -> None:
    from ui import operations_console

    original_raid_notes_card = operations_console.OperationsConsole._raid_notes_card

    def raid_notes_card_editable(self):
        card = original_raid_notes_card(self)
        _clear_card(card)
        self.raid_notes_editor = _note_editor(
            "overview.raid_notes",
            minimum_height=120,
            placeholder="Raid notes…",
        )
        card.addWidget(self.raid_notes_editor)
        return card

    operations_console.OperationsConsole._raid_notes_card = raid_notes_card_editable


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    _install_mechanics()
    _install_overview_raid_notes()
    _INSTALLED = True
