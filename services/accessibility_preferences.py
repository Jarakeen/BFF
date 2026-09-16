from __future__ import annotations

"""Persistent accessibility and display preferences owned by the local Foundry install."""

import json
from pathlib import Path

from engine.config import get_app_root

COLOR_VISION_STANDARD = "standard"
COLOR_VISION_FRIENDLY = "colorblind_friendly"

# Urban Wilderness is intentionally red/green-independent. Keep the historical
# key constants readable for old settings/tests, but expose only the safe mode.
VALID_COLOR_VISION_MODES = frozenset({COLOR_VISION_FRIENDLY})

VISUAL_THEME_FOUNDRY = "foundry_grimoire"
VISUAL_THEME_RYLO = "rylo_grayscale"
VISUAL_THEME_FOUNDRY_FIELD_JOURNAL = "foundry_field_journal"
VISUAL_THEME_RYLO_CITY = "rylo_city_night"
VISUAL_THEME_URBAN_WILDERNESS = VISUAL_THEME_RYLO_CITY
VALID_VISUAL_THEMES = frozenset({VISUAL_THEME_URBAN_WILDERNESS})


def is_rylo_visual_theme(theme: str) -> bool:
    return str(theme or "").strip().casefold() in {
        VISUAL_THEME_RYLO,
        VISUAL_THEME_RYLO_CITY,
    }


def is_foundry_visual_theme(theme: str) -> bool:
    return str(theme or "").strip().casefold() in {
        VISUAL_THEME_FOUNDRY,
        VISUAL_THEME_FOUNDRY_FIELD_JOURNAL,
    }


class AccessibilityPreferences:
    """Read and write the single supported low-stimulation display profile.

    Older theme/color-vision keys are migrated on read rather than deleted. The
    active application profile is always Urban Wilderness plus the colorblind-
    friendly semantic overlay so no saved preference can silently re-enable a
    red/green-dependent or brighter legacy skin.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path)
            if path is not None
            else get_app_root() / "user_data" / "accessibility.json"
        )

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def color_vision_mode(self) -> str:
        return COLOR_VISION_FRIENDLY

    def set_color_vision_mode(self, mode: str) -> str:
        payload = self._read()
        payload["ColorVisionMode"] = COLOR_VISION_FRIENDLY
        payload["VisualTheme"] = VISUAL_THEME_URBAN_WILDERNESS
        self._write(payload)
        return COLOR_VISION_FRIENDLY

    def visual_theme(self) -> str:
        return VISUAL_THEME_URBAN_WILDERNESS

    def set_visual_theme(self, theme: str) -> str:
        payload = self._read()
        payload["VisualTheme"] = VISUAL_THEME_URBAN_WILDERNESS
        payload["ColorVisionMode"] = COLOR_VISION_FRIENDLY
        self._write(payload)
        return VISUAL_THEME_URBAN_WILDERNESS
