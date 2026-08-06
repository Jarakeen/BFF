# ==================================================
# Black Feather Foundry
#
# File:
# widgets/broadcast_briefing.py
#
# Purpose:
# Collects the information required to generate
# a broadcast.
#
# ==================================================

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QComboBox,
    QFormLayout,
    QLineEdit,
)

from widgets.coffee_selector import CoffeeSelector
from widgets.difficulty_selector import DifficultySelector
from widgets.weather_selector import WeatherSelector


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

    weather_source: str

    coffee: str

    coffee_source: str

    coffee_level: str

    engineering: str

    incidents: str

    team: str

    mood: str


class BroadcastBriefing(QWidget):
    """
    Collects all information required for a broadcast.
    """

    def __init__(
        self,
        weather_icon_folder: Path,
        parent=None,
    ):
        super().__init__(parent)

        form = QFormLayout(self)

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

        #
        # Stream
        #

        self.weather = WeatherSelector(
            weather_icon_folder
        )

        self.coffee = CoffeeSelector()

        self.coffee_level = QLineEdit()

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

        form.addRow(
            "EXPEDITION",
            self.focus,
        )

        form.addRow(
            "LOCATION",
            self.location,
        )

        form.addRow(
            "OBJECTIVE",
            self.goal,
        )

        form.addRow(
            "DIFFICULTY",
            self.difficulty,
        )

        form.addRow(
            "WEATHER",
            self.weather,
        )

        form.addRow(
            "COFFEE",
            self.coffee,
        )

        form.addRow(
            "COFFEE LEVEL",
            self.coffee_level,
        )

        form.addRow(
            "ENGINEERING",
            self.engineering,
        )

        form.addRow(
            "INCIDENTS",
            self.incidents,
        )

        form.addRow(
            "TEAM",
            self.team,
        )

        form.addRow(
            "TONE",
            self.mood,
        )

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    @property
    def model(self) -> BroadcastModel:

        return BroadcastModel(

            focus=self.focus.currentText(),

            location=self.location.text(),

            goal=self.goal.text(),

            difficulty=self.difficulty.selected,

            weather=self.weather.currentText(),

            weather_source=self.weather.obs_source,

            coffee=self.coffee.currentText(),

            coffee_source=self.coffee.source_name,

            coffee_level=self.coffee_level.text(),

            engineering=self.engineering.currentText(),

            incidents=self.incidents.text(),

            team=self.team.text(),

            mood=self.mood.currentText(),
        )

    def clear(self):

        self.focus.setCurrentIndex(0)

        self.location.clear()

        self.goal.clear()

        self.difficulty.clear()

        self.weather.reset()

        self.coffee.reset()

        self.coffee_level.clear()

        self.engineering.setCurrentIndex(0)

        self.incidents.clear()

        self.team.clear()

        self.mood.setCurrentIndex(0)