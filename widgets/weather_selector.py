# widgets/weather_selector.py

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox

from services.settings_service import SettingsService


class WeatherSelector(QComboBox):

    OBS_SOURCE_MAP = {
        "Clear": "TOP_clear",
        "Partly Cloudy": "TOP_partly_cloudy",
        "Cloudy": "TOP_cloudy",
        "Light Rain": "TOP_rain_light",
        "Heavy Rain": "TOP_rain_heavy",
        "Storm": "TOP_storm",
        "Fog": "TOP_fog",
        "Snow": "TOP_snow",
        "Windy": "TOP_wind",
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        settings = SettingsService(
            Path("settings.json")
        ).load()

        settings = SettingsService(
            Path("settings.json")
        ).load()

        root = Path(settings["BffRoot"])

        self.weather_icon_folder = (
            root /
            "assets" /
            "weather"
        )

        for weather in self.OBS_SOURCE_MAP:

            icon = self.weather_icon_folder / f"{weather}.png"

            self.addItem(
                QIcon(str(icon)),
                weather,
            )

    @property
    def obs_source(self):

        return self.OBS_SOURCE_MAP[
            self.currentText()
        ]

    def reset(self):

        self.setCurrentIndex(0)