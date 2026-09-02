from __future__ import annotations

"""Persistent accessibility preferences owned by the local Foundry install."""

import json
from pathlib import Path

from engine.config import get_app_root

COLOR_VISION_STANDARD = "standard"
COLOR_VISION_FRIENDLY = "colorblind_friendly"
VALID_COLOR_VISION_MODES = frozenset(
    {COLOR_VISION_STANDARD, COLOR_VISION_FRIENDLY}
)


class AccessibilityPreferences:
    """Read and write small user-facing accessibility preferences.

    This state lives outside data/ because it is a local display preference,
    not ESO reference data. Keeping it beside the executable also makes the
    preference portable in a friend build without baking it into the binary.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else get_app_root() / "user_data" / "accessibility.json"

    def color_vision_mode(self) -> str:
        if not self.path.exists():
            return COLOR_VISION_STANDARD
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return COLOR_VISION_STANDARD
        mode = str(payload.get("ColorVisionMode", COLOR_VISION_STANDARD) or "").strip().casefold()
        return mode if mode in VALID_COLOR_VISION_MODES else COLOR_VISION_STANDARD

    def set_color_vision_mode(self, mode: str) -> str:
        normalized = str(mode or "").strip().casefold()
        if normalized not in VALID_COLOR_VISION_MODES:
            normalized = COLOR_VISION_STANDARD
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"ColorVisionMode": normalized}
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return normalized
