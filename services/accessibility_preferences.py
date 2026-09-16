from __future__ import annotations

"""Persistent accessibility and display preferences owned by the local Foundry install."""

import json
from pathlib import Path

from engine.config import get_app_root

COLOR_VISION_STANDARD = "standard"
COLOR_VISION_FRIENDLY = "colorblind_friendly"
VALID_COLOR_VISION_MODES = frozenset(
    {COLOR_VISION_STANDARD, COLOR_VISION_FRIENDLY}
)

# Historical theme keys remain defined for compatibility with old settings files
# and code paths, but City After Midnight is now the only selectable/active skin.
VISUAL_THEME_FOUNDRY = "foundry_grimoire"
VISUAL_THEME_RYLO = "rylo_grayscale"
VISUAL_THEME_FOUNDRY_FIELD_JOURNAL = "foundry_field_journal"
VISUAL_THEME_RYLO_CITY = "rylo_city_night"
VALID_VISUAL_THEMES = frozenset({VISUAL_THEME_RYLO_CITY})


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
    """Read and write local display/accessibility preferences.

    Display state lives outside data/ because it is local UI state, not ESO
    reference data. Theme migration is intentionally non-destructive: an older
    saved theme key is simply normalized to City After Midnight on read.
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
        payload = self._read()
        mode = str(
            payload.get("ColorVisionMode", COLOR_VISION_STANDARD) or ""
        ).strip().casefold()
        return mode if mode in VALID_COLOR_VISION_MODES else COLOR_VISION_STANDARD

    def set_color_vision_mode(self, mode: str) -> str:
        normalized = str(mode or "").strip().casefold()
        if normalized not in VALID_COLOR_VISION_MODES:
            normalized = COLOR_VISION_STANDARD
        payload = self._read()
        payload["ColorVisionMode"] = normalized
        payload["VisualTheme"] = VISUAL_THEME_RYLO_CITY
        self._write(payload)
        return normalized

    def visual_theme(self) -> str:
        payload = self._read()
        theme = str(payload.get("VisualTheme", VISUAL_THEME_RYLO_CITY) or "").strip().casefold()
        return theme if theme in VALID_VISUAL_THEMES else VISUAL_THEME_RYLO_CITY

    def set_visual_theme(self, theme: str) -> str:
        normalized = str(theme or "").strip().casefold()
        if normalized not in VALID_VISUAL_THEMES:
            normalized = VISUAL_THEME_RYLO_CITY
        payload = self._read()
        payload["VisualTheme"] = normalized
        payload.setdefault("ColorVisionMode", COLOR_VISION_STANDARD)
        self._write(payload)
        return normalized
