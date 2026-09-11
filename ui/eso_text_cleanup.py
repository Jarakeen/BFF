from __future__ import annotations

"""Presentation-safe cleanup for ESO inline text markup.

ESO source text can contain color spans such as ``|cRRGGBB...|r`` and, in a few
imports, extended/malformed 7-8 digit variants.  These tokens are rendering
instructions, not semantic game data, so UI-facing text should remove them.
Canonical mechanics values are not changed by this helper.
"""

import re


_ESO_COLOR_TAG_RE = re.compile(r"\|c[0-9A-Fa-f]{6,8}")


def strip_eso_color_markup(value: object) -> str:
    """Return plain text with ESO color-open and reset tokens removed."""

    return _ESO_COLOR_TAG_RE.sub("", str(value or "")).replace("|r", "")


__all__ = ["strip_eso_color_markup"]
