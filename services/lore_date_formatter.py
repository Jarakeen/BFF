# ==================================================
# Black Feather Foundry
#
# File:
# services/lore_date_formatter.py
#
# Purpose:
# Formats Tamrielic dates for different
# Foundry displays.
#
# ==================================================

from __future__ import annotations


class LoreDateFormatter:
    """
    Formats Tamrielic dates into several
    presentation styles.
    """

    @staticmethod
    def full(
        weekday: str,
        day: int,
        month: str,
        year: str,
    ) -> str:
        """
        Middas, 25th of Sun's Height 2E 582
        """

        return (
            f"{weekday}, "
            f"{LoreDateFormatter.ordinal(day)} "
            f"of {month} "
            f"{year}"
        )

    @staticmethod
    def long(
        day: int,
        month: str,
        year: str,
    ) -> str:
        """
        25th of Sun's Height 2E 582
        """

        return (
            f"{LoreDateFormatter.ordinal(day)} "
            f"of {month} "
            f"{year}"
        )

    @staticmethod
    def short(
        day: int,
        month: str,
    ) -> str:
        """
        25th of Sun's Height
        """

        return (
            f"{LoreDateFormatter.ordinal(day)} "
            f"of {month}"
        )

    @staticmethod
    def compact(
        day: int,
        month: str,
    ) -> str:
        """
        25 Sun's Height
        """

        return f"{day} {month}"

    @staticmethod
    def ordinal(day: int) -> str:
        """
        Convert 1 -> 1st, 2 -> 2nd, etc.
        """

        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {
                1: "st",
                2: "nd",
                3: "rd",
            }.get(day % 10, "th")

        return f"{day}{suffix}"