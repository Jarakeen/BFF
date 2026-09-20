from __future__ import annotations

"""Presentation-safe cleanup for ESO inline text markup.

ESO source text uses color spans such as ``|cRRGGBB...|r``. These tokens are
rendering instructions, not semantic game data, so UI-facing text should remove
them. Canonical mechanics values are not changed by this helper.
"""

import html
import re


# ESO color-open tokens are exactly six hexadecimal RGB digits. Do not make this
# variable-width: visible text may legitimately begin with A-F/0-9, and a greedy
# 7-8 digit match would consume the first character(s) of that text.
_ESO_COLOR_TAG_RE = re.compile(r"\|c[0-9A-Fa-f]{6}", re.IGNORECASE)
_ESO_ANGLE_COLOR_OPEN_RE = re.compile(r"<c(?:olor)?(?:=|:)?[#]?[0-9A-Fa-f]{6,8}>", re.IGNORECASE)
_ESO_ANGLE_COLOR_CLOSE_RE = re.compile(r"</c(?:olor)?>", re.IGNORECASE)
_HTML_FONT_COLOR_OPEN_RE = re.compile(
    r"<font\s+[^>]*color\s*=\s*['\"]?#[0-9A-Fa-f]{3,8}['\"]?[^>]*>",
    re.IGNORECASE,
)
_HTML_FONT_CLOSE_RE = re.compile(r"</font>", re.IGNORECASE)
_HTML_SPAN_COLOR_OPEN_RE = re.compile(
    r"<span\s+[^>]*style\s*=\s*['\"][^'\"]*color\s*:\s*#[0-9A-Fa-f]{3,8}[^'\"]*['\"][^>]*>",
    re.IGNORECASE,
)
_HTML_SPAN_CLOSE_RE = re.compile(r"</span>", re.IGNORECASE)


def strip_eso_color_markup(value: object) -> str:
    """Return display-safe text with ESO/HTML color rendering tokens removed."""

    text = html.unescape(str(value or ""))
    text = _ESO_COLOR_TAG_RE.sub("", text).replace("|r", "")
    text = _ESO_ANGLE_COLOR_OPEN_RE.sub("", text)
    text = _ESO_ANGLE_COLOR_CLOSE_RE.sub("", text)
    text = _HTML_FONT_COLOR_OPEN_RE.sub("", text)
    text = _HTML_FONT_CLOSE_RE.sub("", text)
    text = _HTML_SPAN_COLOR_OPEN_RE.sub("", text)
    text = _HTML_SPAN_CLOSE_RE.sub("", text)
    return text


__all__ = ["strip_eso_color_markup"]
