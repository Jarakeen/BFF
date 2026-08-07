# services/narrator_service.py
from __future__ import annotations

import random
import re
from pathlib import Path


class NarratorService:
    """
    Reads the Natural History Narrator markdown file.

    Categories are markdown headings:

        ## 🦦 General Observations

    followed by bullet points.

    Public API:

        categories()
        pick(category)
    """

    def __init__(self, content_path: Path):
        self.content_path = Path(content_path)

    # --------------------------------------------------
    # Parsing
    # --------------------------------------------------

    def _load(self) -> dict[str, list[str]]:

        if not self.content_path.exists():
            return {}

        text = self.content_path.read_text(
            encoding="utf-8"
        )

        categories: dict[str, list[str]] = {}

        current = None

        for line in text.splitlines():

            line = line.strip()

            #
            # Heading
            #

            if line.startswith("##"):

                heading = re.sub(
                    r"^##\s*",
                    "",
                    line,
                )

                #
                # Remove emoji but keep words
                #

                heading = re.sub(
                    r"^[^\w]+",
                    "",
                    heading,
                ).strip()

                current = heading

                categories[current] = []

                continue

            #
            # Bullet
            #

            if current and line.startswith("-"):

                categories[current].append(
                    line[1:].strip()
                )

        return categories

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def categories(self) -> list[str]:

        
        categories = self._load()

        print("Loaded narrator categories:", categories)


        return list(self._load().keys())



    def pick(self, category: str) -> str:

        categories = self._load()

        choices = categories.get(category, [])

        if not choices:
            return ""

        return random.choice(choices)