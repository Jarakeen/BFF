# widgets/weather_selector.py

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox


class WeatherSelector(QComboBox):
    """
    Standard Black Feather Foundry weather selector.

    Displays weather icons and exposes the
    corresponding OBS source.
    """

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

    def __init__(
        self,
        weather_icon_folder: Path,
        parent=None,
    ):
        super().__init__(parent)

        self.weather_icon_folder = Path(weather_icon_folder)

        for weather in self.OBS_SOURCE_MAP:

            icon_path = (
                self.weather_icon_folder /
                f"{weather}.png"
            )

            self.addItem(
                QIcon(str(icon_path)),
                weather,
            )

    @property
    def obs_source(self) -> str:
        return self.OBS_SOURCE_MAP[self.currentText()]

    def set_source(self, source: str) -> None:

        for label, obs_source in self.OBS_SOURCE_MAP.items():

            if obs_source == source:
                self.setCurrentText(label)
                return

    def reset(self):

        self.setCurrentText("Clear")