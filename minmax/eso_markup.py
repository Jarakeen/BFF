from dataclasses import dataclass
import re
from typing import Union


Number = Union[int, float]


@dataclass(frozen=True)
class EsoMarkupToken:
    raw: str
    color: str
    value_text: str
    value: Number | None


@dataclass(frozen=True)
class EsoMarkupResult:
    text: str
    tokens: tuple[EsoMarkupToken, ...]


# ESO formatted value:
# |cRRGGBBVALUE|r
#
# We deliberately keep VALUE permissive enough to preserve unusual
# values rather than trying to interpret ESO mechanics here.
_FORMATTED_VALUE_RE = re.compile(
    r"\|c(?P<color>[0-9A-Fa-f]{6})(?P<value>.*?)\|r"
)


def _parse_value(value_text: str) -> Number | None:
    """
    Convert a simple numeric value to int/float.

    Return None for values that are not safely numeric.
    The original value_text is always preserved separately.
    """
    text = value_text.strip()

    if not text:
        return None

    try:
        if re.fullmatch(r"[+-]?\d+", text):
            return int(text)

        if re.fullmatch(
            r"[+-]?(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?",
            text,
        ):
            return float(text)

        if re.fullmatch(
            r"[+-]?\d+(?:[eE][+-]?\d+)",
            text,
        ):
            return float(text)

    except (ValueError, OverflowError):
        pass

    return None


def normalize_eso_markup(text: str) -> EsoMarkupResult:
    """
    Normalize ESO formatted-value markup.

    Example:

        "closest |cffffff5|r members within |cffffff28|r meters"

    becomes:

        "closest 5 members within 28 meters"

    The original markup tokens are preserved in the result.

    This function performs NO ESO game-mechanics interpretation.
    """
    if not text:
        return EsoMarkupResult(text=text, tokens=())

    tokens: list[EsoMarkupToken] = []

    def replace(match: re.Match[str]) -> str:
        color = match.group("color")
        value_text = match.group("value")
        raw = match.group(0)

        token = EsoMarkupToken(
            raw=raw,
            color=color,
            value_text=value_text,
            value=_parse_value(value_text),
        )

        tokens.append(token)

        return value_text

    normalized = _FORMATTED_VALUE_RE.sub(replace, text)

    return EsoMarkupResult(
        text=normalized,
        tokens=tuple(tokens),
    )
