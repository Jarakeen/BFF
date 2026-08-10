# ==================================================
# Black Feather Foundry
#
# File:
# engine/parsers/base_parser.py
#
# Purpose:
# Shared infrastructure for Foundry data parsers.
#
# This class does NOT interpret ESO mechanics.
# It provides common tools for:
# - loading raw data
# - normalizing values
# - grouping records
# - writing derived data
#
# ==================================================

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict
from typing import Any


class BaseParser:
    """
    Base class for Foundry data parsers.

    Subclasses are responsible for understanding
    specific ESO data types.

    BaseParser only handles infrastructure.
    """

    def __init__(
        self,
        raw_folder: str | Path,
        output_folder: str | Path,
    ):
        self.raw_folder = Path(raw_folder)
        self.output_folder = Path(output_folder)

        self.output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    # --------------------------------------------------
    # File I/O
    # --------------------------------------------------

    def load_json(
        self,
        filename: str,
    ) -> Any:

        path = self.raw_folder / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Raw data file not found: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    def write_json(
        self,
        filename: str,
        data: Any,
    ) -> Path:

        path = self.output_folder / filename

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )

        return path

    # --------------------------------------------------
    # Value helpers
    # --------------------------------------------------

    @staticmethod
    def clean_string(
        value: Any,
    ) -> str | None:

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value

    @staticmethod
    def to_int(
        value: Any,
        default: int | None = None,
    ) -> int | None:

        if value is None:
            return default

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def to_float(
        value: Any,
        default: float | None = None,
    ) -> float | None:

        if value is None:
            return default

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def to_bool(
        value: Any,
    ) -> bool:

        if isinstance(value, bool):
            return value

        if value is None:
            return False

        return str(value).lower() in {
            "1",
            "true",
            "yes",
        }

    # --------------------------------------------------
    # Grouping
    # --------------------------------------------------

    @staticmethod
    def group_by(
        records: list[dict],
        key: str,
    ) -> dict[str, list[dict]]:

        groups: dict[str, list[dict]] = defaultdict(list)

        for record in records:

            value = record.get(key)

            if value is None:
                continue

            groups[str(value)].append(
                record
            )

        return dict(groups)

    # --------------------------------------------------
    # Deduplication
    # --------------------------------------------------

    @staticmethod
    def unique_by(
        records: list[dict],
        key: str,
    ) -> list[dict]:

        seen = set()
        result = []

        for record in records:

            value = record.get(key)

            if value in seen:
                continue

            seen.add(value)
            result.append(record)

        return result