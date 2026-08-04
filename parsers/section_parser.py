import re


class SectionParser:
    """
    Base class for parsers that extract sections from a document.
    """

    def extract_section(
        self,
        text: str,
        start: str,
        end: str | None = None,
    ) -> str:

        start_match = re.search(re.escape(start), text)

        if not start_match:
            return ""

        start_index = start_match.end()

        if end:

            end_match = re.search(
                re.escape(end),
                text[start_index:]
            )

            if end_match:

                end_index = start_index + end_match.start()

                return text[start_index:end_index].strip()

        return text[start_index:].strip()

    def is_heading(self, line: str) -> bool:

        line = line.rstrip()

        return bool(line) and not line.startswith(" ")