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

    focus: str
    location: str
    goal: str
    difficulty: list[str]

    weather: str
    coffee: str
    coffee_level: str

    engineering: str
    incidents: str
    team: str
    mood: str


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

        self.coffee_level = CoffeeLevelWidget()

        self.coffee_level.set_generator(
            lambda: f"{random.randint(0, 100)}%"
)

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
        form.addRow("Coffee Level", self.coffee_level)
        form.addRow("Engineering", self.engineering)
        form.addRow("Incidents", self.incidents)
        form.addRow("Team", self.team)
        form.addRow("Tone", self.mood)

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    @property
    def model(self) -> BroadcastModel:

        return BroadcastModel(
            focus=self.focus.currentText(),
            location=self.location.text().strip(),
            goal=self.goal.text().strip(),
            difficulty=self.difficulty.selected,
            weather=self.weather.currentText(),
            coffee=self.coffee.currentText(),
            coffee_level=self.coffee_level.level,
            engineering=self.engineering.currentText(),
            incidents=self.incidents.text().strip(),
            team=self.team.text().strip(),
            mood=self.mood.currentText(),
        )

    @property
    def level(self) -> str:
        return self.edit.text().strip()

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def clear(self):

        self.focus.setCurrentIndex(0)

        self.location.clear()

        self.goal.clear()

        self.difficulty.clear()

        if hasattr(self.weather, "reset"):
            self.weather.reset()
        else:
            self.weather.setCurrentIndex(0)

        if hasattr(self.coffee, "reset"):
            self.coffee.reset()
        else:
            self.coffee.setCurrentIndex(0)

        self.coffee_level.clear()

        self.engineering.setCurrentIndex(0)

        self.incidents.clear()

        self.team.clear()

        self.mood.setCurrentIndex(0)