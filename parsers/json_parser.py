# ==================================================
# Black Feather Foundry
#
# File:
# parsers/json_parser.py
#
# Purpose:
# Base class for parsers that read JSON files.
#
# ==================================================

from __future__ import annotations

import json

from pathlib import Path


class JsonParser:
    """
    Base class for JSON parsers.
    """

    def __init__(self):

        self._cache: dict[Path, object] = {}

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def load(
        self,
        path: Path,
    ):

        path = Path(path)

        if path not in self._cache:

            self._cache[path] = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        return self._cache[path]

    def clear_cache(self):

        self._cache.clear()

    def exists(
    self,
    path: Path,
    ) -> bool:

        return Path(path).exists()    