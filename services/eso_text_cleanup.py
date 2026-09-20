from __future__ import annotations

"""Shared plain-text cleanup for ESO rendering markup.

ESO source strings can contain client color tokens or HTML-like color wrappers.
Those tokens are presentation instructions, not semantic game data. This helper
preserves the visible text and removes only color-rendering markup.
"""

import html
import re


_ESO_COLOR_TAG_RE = re.compile(r"\|c[0-9A-Fa-f]{6}", re.IGNORECASE)
_ESO_ANGLE_COLOR_OPEN_RE = re.compile(
    r"<c(?:olor)?(?:=|:)?[#]?[0-9A-Fa-f]{6,8}>",
    re.IGNORECASE,
)
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
    """Return text with ESO and HTML color-rendering wrappers removed."""

    text = html.unescape(str(value or ""))
    text = _ESO_COLOR_TAG_RE.sub("", text).replace("|r", "")
    text = _ESO_ANGLE_COLOR_OPEN_RE.sub("", text)
    text = _ESO_ANGLE_COLOR_CLOSE_RE.sub("", text)
    text = _HTML_FONT_COLOR_OPEN_RE.sub("", text)
    text = _HTML_FONT_CLOSE_RE.sub("", text)
    text = _HTML_SPAN_COLOR_OPEN_RE.sub("", text)
    text = _HTML_SPAN_CLOSE_RE.sub("", text)
    return text


def clean_eso_text(value: object) -> str:
    """Return compact display/storage text after stripping color markup."""

    return " ".join(strip_eso_color_markup(value).split())


__all__ = ["clean_eso_text", "strip_eso_color_markup"]
