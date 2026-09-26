from __future__ import annotations

"""Persistent accessibility and display preferences owned by the local Foundry install."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from services.settings_pydantic_schema import validate_accessibility_payload

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
            return validate_accessibility_payload(payload)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Accessibility preferences failed strict validation: {exc}") from exc

    def _write(self, payload: dict) -> None:
        try:
            persisted = validate_accessibility_payload(payload)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Accessibility preferences failed strict validation: {exc}") from exc
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp", delete=False) as handle:
                temporary_path = Path(handle.name)
                json.dump(persisted, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        read_back = validate_accessibility_payload(json.loads(self.path.read_text(encoding="utf-8")))
        if read_back != persisted:
            raise RuntimeError("Accessibility preferences did not round-trip exactly")

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
