from __future__ import annotations

"""Canonical non-player labels that must never become Personnel identities."""

PERSONNEL_PLACEHOLDER_NAMES: tuple[str, ...] = (
    "Tank 1",
    "Tank 2",
    "Healer 1",
    "Healer 2",
    "DD 1",
    "DD 2",
    "DD 3",
    "DD 4",
    "DD 5",
    "DD 6",
    "DD 7",
    "DD 8",
    "Recruitment Needed",
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def is_personnel_placeholder(value: object) -> bool:
    text = _clean(value).casefold()
    return text in {name.casefold() for name in PERSONNEL_PLACEHOLDER_NAMES}


__all__ = ["PERSONNEL_PLACEHOLDER_NAMES", "is_personnel_placeholder"]
