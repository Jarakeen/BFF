# parsers/dialogue_parser.py
import re

from models.boss import DialogueGroup


class DialogueParser:

    def parse(self, text: str) -> list[DialogueGroup]:

        section = self.extract_section(
            text,
            "Dialogue",
            "Notes",
        )

        groups = []

        current_trigger = None
        current_lines = []

        for line in section.splitlines():

            line = line.rstrip()

            if not line:
                continue

            if line.endswith(":") and not line.startswith(" "):

                if current_trigger:

                    groups.append(
                        DialogueGroup(
                            trigger=current_trigger,
                            lines=current_lines,
                        )
                    )

                current_trigger = line[:-1].strip()
                current_lines = []

            else:

                line = line.strip()

                # Remove "Flame-Herald Bahsei:"
                line = re.sub(
                    r"^[^:]+:\s*",
                    "",
                    line,
                )

                  # Remove surrounding quotation marks
                line =line.strip('"')
                line =line.strip('"')
                line =line.strip("“”")
                line =line.strip("'")

                    # Ignore unknown dialogue placeholders
                if line == "(?)":
                        continue

                current_lines.append(line)

        if current_trigger:

            groups.append(
                DialogueGroup(
                    trigger=current_trigger,
                    lines=current_lines,
                )
            )

        return groups

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