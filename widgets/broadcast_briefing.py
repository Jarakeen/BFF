# ==================================================
# Black Feather Foundry
#
# File:
# widgets/broadcast_briefing.py
#
# Purpose:
# Collect information required to prepare
# a broadcast.
#
# ==================================================

from __future__ import annotations

from dataclasses import dataclass
import random

from PySide6.QtWidgets import (
    QWidget,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QGroupBox,
    QPushButton,
    QTextEdit,
)

from widgets.coffee_selector import CoffeeSelector
from widgets.difficulty_selector import DifficultySelector
from widgets.weather_selector import WeatherSelector
from widgets.coffee_level_widget import CoffeeLevelWidget

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


@dataclass
class BroadcastModel:
    expedition: str
    focus: str
    location: str
    goal: str
    difficulty: str

    weather: str
    coffee: str
    coffeeLevel: str

    engineering: str
    incidents: str
    team: str
    mood: str

    custom_title: str = ""
    custom_notification: str = ""

    clipBoard: str = ""
    content: str = ""
    context: str = ""
    nextSteps : str = ""


class BroadcastBriefing(QWidget):
    """
    Broadcast briefing editor.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        #
        # Expedition
        #

        self.focus = QComboBox()
        self.focus.addItems([
            "Trials",
            "Dungeons",
            "Achievement Hunt",
            "Progression Night",
            "Field Notes",
            "Open Expedition",
        ])

        self.location = QLineEdit()

        self.goal = QLineEdit()

        self.difficulty = DifficultySelector()

        self.coffee = CoffeeLevelWidget()
        #
        # Broadcast
        #

        self.weather = WeatherSelector()

        self.coffee = CoffeeSelector()

        self.coffeeLevel = CoffeeLevelWidget()

        self.coffeeLevel.set_generator(
            lambda: f"{random.randint(0, 100)}%"
)
        self.clipBoard = QLineEdit()
        self.engineering = QComboBox()
        self.engineering.setEditable(True)
        self.engineering.addItems(OTTER_VARIABLES)

        self.incidents = QLineEdit()

        self.team = QLineEdit()

        self.mood = QComboBox()
        self.mood.addItems([
            "Focused",
            "Funny",
            "Questing",
            "Hardmode",
        ])

        self.broadcast_custom_title_edit = QLineEdit()

        self.broadcast_custom_title_edit.setPlaceholderText(
            "Enter your own stream title..."
        )

        self.broadcast_custom_notification_edit = QLineEdit()

        self.broadcast_custom_notification_edit.setPlaceholderText(
            "Enter your own live notification..."
        )

    
        #
        # Layout
        #
        

        form = QFormLayout(self)

        form.addRow("Expedition", self.focus)
        form.addRow("Location", self.location)
        form.addRow("Objective", self.goal)
        form.addRow("Difficulty", self.difficulty)
        form.addRow("Weather", self.weather)
        form.addRow("Coffee", self.coffee)
        form.addRow("Coffee Level", self.coffeeLevel)
        form.addRow("Engineering", self.engineering)
        form.addRow("Incidents", self.incidents)
        form.addRow("Team", self.team)
        form.addRow("Tone", self.mood)
        form.addRow(
            "Your Own Stream Title",
            self.broadcast_custom_title_edit
        )

        form.addRow(
            "Your Own Live Notification",
            self.broadcast_custom_notification_edit
        )
    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    @property
    def model(self) -> BroadcastModel:

        return BroadcastModel(
            expedition=self.location.text().strip(),
            focus=self.focus.currentText(),
            location=self.location.text().strip(),
            goal=self.goal.text().strip(),
            difficulty=self.difficulty.selected,
            weather=self.weather.currentText(),
            coffee=self.coffee.currentText(),
            coffeeLevel=self.coffeeLevel.level,
            engineering=self.engineering.currentText(),
            incidents=self.incidents.text().strip(),
            team=self.team.text().strip(),
            mood=self.mood.currentText(),
            custom_title=self.broadcast_custom_title_edit.text().strip(),
            custom_notification=self.broadcast_custom_notification_edit.text().strip(),
        )
   

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def clear(self):

        self.focus.setCurrentIndex(0)

        self.location.clear()

        self.goal.clear()
        self.clipBoard.clear()
        self.difficulty.clear()

        if hasattr(self.weather, "reset"):
            self.weather.reset()
        else:
            self.weather.setCurrentIndex(0)

        if hasattr(self.coffee, "reset"):
            self.coffee.reset()
        else:
            self.coffee.setCurrentIndex(0)

        self.coffeeLevel.clear()

        self.engineering.setCurrentIndex(0)

        self.incidents.clear()

        self.team.clear()

        self.mood.setCurrentIndex(0)