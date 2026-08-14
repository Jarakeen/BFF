# ui/broadcast_page.py
from __future__ import annotations


import json
import random
from datetime import datetime
from pathlib import Path
import re
from widgets.weather_selector import WeatherSelector
from widgets.coffee_selector import CoffeeSelector
from widgets.page_header import PageHeader


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

OTTER_VARIABLES = [
    "Nominal",
    "Recursive",
    "Sentient",
    "Unsupervised",
    "Orthogonal",
    "Ceremonial",
    "Migratory",
    "Seasonal",
    "Temporal",
    "Peripheral",
    "Ambient",
    "Speculative",
    "Probabilistic",
    "Inexplicable",
    "Contrarian",
    "Percolating",
    "Ferrous",
    "Buoyant",
    "Obstinate",
    "Misfiled",
]







def _build_broadcast_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(

        PageHeader(
        title="Broadcast Desk",
        subtitle="Prepare today's field dispatch.",
        department="Communications",
    )

        )   
    
        intro.setObjectName("broadcastIntro")
        intro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(intro)

        briefing = QGroupBox("Tonight's Briefing")
        form = QFormLayout(briefing)
        self.broadcast_focus_combo = QComboBox()
        self.broadcast_focus_combo.addItems(["Trials", "Dungeons", "Achievement Hunt", "Progression Night", "Field Notes", "Open Expedition"])
        self.broadcast_focus_combo.currentTextChanged.connect(self.on_broadcast_focus_changed)

        # Location swaps between free text and a Trial/Dungeon dropdown
        # depending on what's picked in EXPEDITION TYPE above.
        self.broadcast_location_stack = QStackedWidget()
        self.broadcast_location_edit = QLineEdit()
        self.broadcast_location_edit.setPlaceholderText("e.g. Black Rose Prison, Cloudrest, or Tamriel")
        self.broadcast_location_combo = QComboBox()
        self.broadcast_location_combo.setEditable(True)
        self.broadcast_location_stack.addWidget(self.broadcast_location_edit)  # index 0: free text
        self.broadcast_location_stack.addWidget(self.broadcast_location_combo)  # index 1: dropdown

        self.broadcast_goal_edit = QLineEdit()
        self.broadcast_goal_edit.setPlaceholderText("e.g. Perfecta practice, no-death attempt, or cozy collecting")
        self.broadcast_mood_combo = QComboBox()
        self.broadcast_mood_combo.addItems(["Focused", "Funny", "Questing", "Hardmode"])
        self.broadcast_team_edit = QLineEdit()
        self.broadcast_team_edit.setPlaceholderText("e.g. Black Feather Foundry")

        difficulty_row = QHBoxLayout()
        self.broadcast_difficulty_checkboxes = {
            "Normal": QCheckBox("Normal"),
            "Veteran": QCheckBox("Veteran"),
            "Hardmode": QCheckBox("Hardmode"),
        }
        for checkbox in self.broadcast_difficulty_checkboxes.values():
            difficulty_row.addWidget(checkbox)
        difficulty_row.addStretch(1)

        
        self.broadcast_weather = WeatherSelector(
        self.settings.weather_icon_folder
        )

        self.broadcast_coffee = CoffeeSelector()
        self.broadcast_coffee_level = self._build_field("Coffee Level")
        self.broadcast_engineering = QComboBox()
        self.broadcast_engineering.setEditable(True)
        self.broadcast_engineering.addItems(OTTER_VARIABLES)
        self.broadcast_engineering.setCurrentText("")
        self.broadcast_incidents = self._build_field("Incidents")


        coffee_level_row = QHBoxLayout()
        coffee_level_row.addWidget(self.broadcast_coffee_level)

        coffee_level_randomize_btn = QPushButton()
        coffee_level_randomize_btn.setIcon(self.icons.get("dice"))

        # Set the ICON size here
        coffee_level_randomize_btn.setIconSize(QSize(26, 26))

        # Make sure the button is large enough
        coffee_level_randomize_btn.setFixedSize(34, 34)
        coffee_level_randomize_btn.setToolTip("Randomize coffee level")
        coffee_level_randomize_btn.clicked.connect(self.randomize_coffee_level)
        coffee_level_row.addWidget(coffee_level_randomize_btn)

        form.addRow("EXPEDITION TYPE", self.broadcast_focus_combo)
        form.addRow("LOCATION / CONTENT", self.broadcast_location_stack)
        form.addRow("TONIGHT'S GOAL", self.broadcast_goal_edit)
        form.addRow("DIFFICULTY", difficulty_row)
        form.addRow("WEATHER", self.broadcast_weather)
        form.addRow("COFFEE", self.broadcast_coffee)
        form.addRow("COFFEE LEVEL", coffee_level_row)
        form.addRow("ENGINEERING", self.broadcast_engineering)
        form.addRow("INCIDENT COUNTER", self.broadcast_incidents)
       
        form.addRow("TEAM NAME", self.broadcast_team_edit)
        #
        # Right Side - Broadcast Generator
        #

        generator = QGroupBox("Broadcast Generator")
        generator_layout = QVBoxLayout(generator)

        #
        # Generation Style
        #
    
        style_group = QGroupBox("Generation Style")
        style_layout = QVBoxLayout(style_group)
        # form.addRow("TONE", self.broadcast_mood_combo)
        style_layout.addWidget(self.broadcast_mood_combo)
        generator_layout.addWidget(style_group)

        #
        # Generate Button
        #

        generate_btn = QPushButton("Generate Broadcast Copy")
        generate_btn.clicked.connect(self.generate_broadcast_copy)
        generator_layout.addWidget(generate_btn)

        #
        # Output Lists
        #

        output_row = QHBoxLayout()

        #
        # Stream Titles
        #

        title_box = QGroupBox("Stream Titles (click to copy)")
        title_layout = QVBoxLayout(title_box)

        self.stream_title_list = QListWidget()
        self.stream_title_list.itemClicked.connect(
            lambda item: self.copy_broadcast_text(
                item.text(),
                "Stream title copied"
            )
        )

        title_layout.addWidget(self.stream_title_list)
        output_row.addWidget(title_box)

        #
        # Notifications
        #

        notification_box = QGroupBox("Live Notifications (click to copy)")
        notification_layout = QVBoxLayout(notification_box)

        self.live_notification_list = QListWidget()
        self.live_notification_list.setWordWrap(True)
        self.live_notification_list.itemClicked.connect(
            lambda item: self.copy_broadcast_text(
                item.text(),
                "Live notification copied"
            )
        )

        notification_layout.addWidget(self.live_notification_list)
        output_row.addWidget(notification_box)

        generator_layout.addLayout(output_row)

        #
        # Left + Right Columns
        #

        top_row = QHBoxLayout()

        top_row.addWidget(briefing, 1)
        top_row.addWidget(generator, 1)

        layout.addLayout(top_row)

        actions = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        obs_btn = QPushButton("Save to OBS")
        archive_btn = QPushButton("Save to Archive")
        clear_btn.clicked.connect(self.clear_broadcast)
        obs_btn.clicked.connect(self.save_broadcast_to_obs)
        archive_btn.clicked.connect(self.archive_broadcast)
        actions.addWidget(clear_btn)
        actions.addWidget(obs_btn)
        actions.addWidget(archive_btn)
        layout.addLayout(actions)

        layout.addStretch(1)
        return page

def on_broadcast_focus_changed(self, focus: str) -> None:
        if focus == "Trials":
            names = [n for n in self.eso_data_service.subcategories("Trials") if n != "General"]
            self.broadcast_location_combo.clear()
            self.broadcast_location_combo.addItems(sorted(names))
            self.broadcast_location_stack.setCurrentWidget(self.broadcast_location_combo)
        elif focus == "Dungeons":
            names = [n for n in self.eso_data_service.subcategories("Dungeons") if n != "General"]
            names += [n for n in self.eso_data_service.subcategories("DLC Dungeons") if n != "General"]
            self.broadcast_location_combo.clear()
            self.broadcast_location_combo.addItems(sorted(names))
            self.broadcast_location_stack.setCurrentWidget(self.broadcast_location_combo)
        else:
            self.broadcast_location_stack.setCurrentWidget(self.broadcast_location_edit)

def _broadcast_location_text(self) -> str:
        if self.broadcast_location_stack.currentWidget() is self.broadcast_location_combo:
            return self.broadcast_location_combo.currentText().strip()
        return self.broadcast_location_edit.text().strip()

def generate_broadcast_copy(self) -> None:
        focus = self.broadcast_focus_combo.currentText()
        location = self._broadcast_location_text() or "the field"
        goal = self.broadcast_goal_edit.text().strip() or "documenting the expedition"
        mood = self.broadcast_mood_combo.currentText()
        team = self.broadcast_team_edit.text().strip()

        titles = self._generate_stream_titles(focus, location, goal, mood)
        if team:
            titles = [f"{title} — {team}" for title in titles]
        notifications = self._generate_live_notifications(focus, location, goal, mood)

        self.stream_title_list.clear()
        self.stream_title_list.addItems(titles)
        self.live_notification_list.clear()
        self.live_notification_list.addItems(notifications)
        self.status_label.setText(f"Generated {len(titles)} titles and {len(notifications)} notifications")

@staticmethod
def _generate_stream_titles(focus: str, location: str, goal: str, mood: str) -> list[str]:
        mood_lower = mood.lower()
        candidates = [
            f"Field Notes: {location} — {goal}",
            f"{location} Survey, Continued",
            f"Documenting {location} Tonight",
            f"Foundry Field Report — {location}",
            f"An Expedition to {location}",
            f"{location}: Observations in Progress",
            f"Cataloging {location} — {goal}",
            f"Field Office Live: {location}",
            f"Weather Permitting: {location}",
            f"Tonight's Log: {location} ({mood})",
            f"Routine Survey — {location}",
            f"{goal}, Documented Live from {location}",
        ]
        seen = set()
        unique = []
        for title in candidates:
            if title not in seen:
                seen.add(title)
                unique.append(title)
        return unique[:10]

@staticmethod
def _generate_live_notifications(focus: str, location: str, goal: str, mood: str) -> list[str]:
        mood_lower = mood.lower()
        goal_lower = goal[:1].lower() + goal[1:] if goal else goal
        candidates = [
            f"The Foundry has resumed operations at {location}. Tonight's objective: {goal}. Findings to follow.",
            f"Field notes are being taken at {location}. Conditions: {mood_lower}.",
            f"An expedition has been dispatched to {location}. Purpose: {goal}.",
            f"Observed: the crew has returned to {location}. Documentation ongoing.",
            f"Tonight's survey covers {location}. Objective: {goal}. Weather: {mood_lower}.",
            f"The archive grows. Tonight: {location}, {goal_lower}.",
            f"Field Office open. Currently investigating {location}. No further remarks at this time.",
            f"Routine documentation of {location} is underway. All quiet so far.",
        ]
        trimmed = []
        for text in candidates:
            if len(text) > 140:
                text = text[:137].rstrip() + "..."
            trimmed.append(text)
        seen = set()
        unique = []
        for text in trimmed:
            if text not in seen:
                seen.add(text)
                unique.append(text)
        return unique[:8]

def copy_broadcast_text(self, text: str, status: str) -> None:
        if not text.strip():
            self.status_label.setText("Generate the broadcast copy first")
            return
        QApplication.clipboard().setText(text)
        self.status_label.setText(status)

def clear_broadcast(self) -> None:
        self.broadcast_focus_combo.setCurrentIndex(0)
        self.broadcast_location_stack.setCurrentWidget(self.broadcast_location_edit)
        self.broadcast_location_edit.clear()
        self.broadcast_goal_edit.clear()
        self.broadcast_mood_combo.setCurrentIndex(0)
        self.broadcast_team_edit.clear()
        for checkbox in self.broadcast_difficulty_checkboxes.values():
            checkbox.setChecked(False)
        if self.broadcast_weather.count() > 0:
            self.broadcast_weather.setCurrentIndex(0)
        if self.broadcast_coffee.count() > 0:
            self.broadcast_coffee.setCurrentIndex(0)
        self.broadcast_coffee_level.clear()
        self.broadcast_engineering.setCurrentText("")
        self.broadcast_incidents.clear()
        self.stream_title_list.clear()
        self.live_notification_list.clear()
        self.refresh_top_bar_summary()
        self.status_label.setText("Broadcast Desk cleared")

def save_broadcast_to_obs(self) -> None:
        try:
            # This is the actual fix: the shared expedition fields (Expedition,
            # Difficulty, Objective, Weather, Coffee, Coffee Level, Engineering,
            # Incidents) need to go into CurrentExpedition.json via json_service -
            # that's the only file the Lua script actually reads. Previously this
            # button wrote everything into CurrentBroadcast.json instead, which
            # nothing on the OBS side ever polls, so nothing could ever change
            # on screen no matter what you set here.
            model = self._collect_model()
            self.json_service.save(model)

            title_item = self.stream_title_list.currentItem()
            notification_item = self.live_notification_list.currentItem()
            broadcast_payload = {
                "Title": title_item.text() if title_item else "",
                "Notification": notification_item.text() if notification_item else "",
                "Team": self.broadcast_team_edit.text().strip(),
            }
            self.current_broadcast_path.parent.mkdir(parents=True, exist_ok=True)
            self.current_broadcast_path.write_text(
                json.dumps(broadcast_payload, ensure_ascii=False, indent=4), encoding="utf-8"
            )

            if title_item and notification_item:
                self.status_label.setText("Saved to OBS - expedition data, title, and notification")
            else:
                self.status_label.setText(
                    "Saved to OBS - expedition data updated (pick a title/notification too if you want those included)"
                )
        except Exception as exc:  # pragma: no cover - UI path guard
            self.status_label.setText(f"Save to OBS failed: {exc}")

def archive_broadcast(self) -> None:
        title_item = self.stream_title_list.currentItem()
        notification_item = self.live_notification_list.currentItem()
        if not title_item or not notification_item:
            self.status_label.setText("Click a title and a notification in the lists first, then Save to Archive")
            return
        try:
            focus = self.broadcast_focus_combo.currentText()
            location = self._broadcast_location_text() or "the field"
            goal = self.broadcast_goal_edit.text().strip()
            mood = self.broadcast_mood_combo.currentText()
            team = self.broadcast_team_edit.text().strip()
            difficulty = self._current_difficulty_text()
            weather = self.broadcast_weather.currentText()
            coffee = self.broadcast_coffee.currentText()
            coffee_level = self.broadcast_coffee_level.text()
            engineering = self.broadcast_engineering.currentText()
            incidents = self.broadcast_incidents.text()
            title = title_item.text()
            notification = notification_item.text()

            def build_lines(report_id: str, number: int) -> list[str]:
                return [
                    f"# Broadcast {report_id}",
                    "",
                    f"- Expedition Type: {focus}",
                    f"- Location / Content: {location}",
                    f"- Difficulty: {difficulty or 'None recorded'}",
                    f"- Tonight's Goal: {goal or 'None recorded'}",
                    f"- Weather: {weather}",
                    f"- Coffee: {coffee}",
                    f"- Coffee Level: {coffee_level or 'None recorded'}",
                    f"- Engineering: {engineering or 'None recorded'}",
                    f"- Incidents: {incidents or 'None recorded'}",
                    f"- Tone: {mood}",
                    f"- Team: {team or 'None recorded'}",
                    f"- Title: {title}",
                    f"- Notification: {notification}",
                    f"- Filed: {datetime.now().isoformat(timespec='seconds')}",
                    "",
                ]

            report_id, path = self.archive_service.file_form("EX", build_lines)
            self.status_label.setText(f"Broadcast archived: {report_id} ({path.name})")
        except OSError as exc:
            self.status_label.setText(f"Broadcast archive failed: {exc}")

@staticmethod
def _eso_run_content() -> list[str]:
        # Full list of Trials, base Dungeons, and DLC Dungeons pulled directly
        # from the parsed ESO achievement category tree (esoAchievementData50.php),
        # so this stays accurate to the actual game rather than a hand-typed
        # subset. The combo box is editable, so anything missing (very recent
        # zones not yet in that data export) can still be typed in manually.
        return [
            "Aetherian Archive", "Arx Corinium", "Asylum Sanctorium", "Bal Sunnar",
            "Banished Cells I", "Banished Cells II", "Bedlam Veil", "Black Drake Villa",
            "Black Gem Foundry", "Blackheart Haven", "Blessed Crucible", "Bloodroot Forge",
            "Castle Thorn", "City of Ash I", "City of Ash II", "Cloudrest", "Coral Aerie",
            "Cradle of Shadows", "Crypt of Hearts I", "Crypt of Hearts II",
            "Darkshade Caverns I", "Darkshade Caverns II", "Depths of Malatar",
            "Direfrost Keep", "Dread Cellar", "Dreadsail Reef", "Earthen Root Enclave",
            "Elden Hollow I", "Elden Hollow II", "Exiled Redoubt", "Falkreath Hold",
            "Fang Lair", "Frostvault", "Fungal Grotto I", "Fungal Grotto II",
            "Graven Deep", "Halls of Fabrication", "Hel Ra Citadel", "Icereach",
            "Imperial City Prison", "Kyne's Aegis", "Lair of Maarselok", "Lep Seclusa",
            "Lucent Citadel", "March of Sacrifices", "Maw of Lorkhaj", "Moon Hunter Keep",
            "Moongrave Fane", "Naj-Caldeesh", "Oathsworn Pit", "Ossein Cage",
            "Red Petal Bastion", "Rockgrove", "Ruins of Mazzatun", "Sanctum Ophidia",
            "Sanity's Edge", "Scalecaller Peak", "Scrivener's Hall", "Selene's Web",
            "Shipwright's Regret", "Spindleclutch I", "Spindleclutch II", "Stone Garden",
            "Sunspire", "Tempest Island", "The Cauldron", "Unhallowed Grave",
            "Vaults of Madness", "Volenfell", "Wayrest Sewers I", "Wayrest Sewers II",
            "White Gold Tower",
            # Arenas (solo/duo, but achievement hunters track these too)
            "Blackrose Prison", "Dragonstar Arena", "Maelstrom Arena", "Vateshran Hollows",
        ]


def _build_weather_selector(self) -> QComboBox:
        combo = QComboBox()
        for label in WEATHER_SOURCE_MAP:
            combo.addItem(label)
        return combo

def _build_coffee_selector(self) -> QComboBox:
        combo = QComboBox()
        for label in COFFEE_SOURCE_MAP:
            combo.addItem(label)
        return combo