# parsers/notes_parser.py

import re


class NotesParser:
    """
    Extracts the Notes section from a boss article.
    """

    def parse(self, text: str) -> list[str]:

        section = self.extract_section(
            text,
            "Notes",
        )

        notes = []

        for line in section.splitlines():

            line = line.strip()

            if not line:
                continue

            # Remove bullet characters if present
            line = line.removeprefix("•").strip()
            line = line.removeprefix("*").strip()

            notes.append(line)

        return notes

    def extract_section(
        self,
        text: str,
        start: str,
        end: str | None = None,
    ) -> str:

        start_match = re.search(
            re.escape(start),
            text,
        )

        if not start_match:
            return ""

        start_index = start_match.end()

        if end:

            end_match = re.search(
                re.escape(end),
                text[start_index:],
            )

            if end_match:

                end_index = start_index + end_match.start()

                return text[start_index:end_index].strip()

        return text[start_index:].strip()