# parsers/health_parser.py
import re

from models.boss import Health


class HealthParser:
    """
    Extracts boss health values from a cleaned UESP boss article.
    """

    def extract_health_block(self, text: str) -> str:

        match = re.search(
            r"Health(.*?)(Reaction|Other Information)",
            text,
            re.DOTALL,
        )

        if match:
            return match.group(1)

        return ""


    def parse(self, text: str) -> Health:

        return Health(
            normal=self.extract_normal(text),
            veteran=self.extract_veteran(text),
            hardmode=self.extract_hardmode(text),
        )

    # --------------------------------------------------
    # Individual Health Values
    # --------------------------------------------------

    def extract_normal(self, text: str) -> int:

        match = re.search(
            r"Normal\s*([\d,]+)",
            text,
            re.IGNORECASE,
        )

        if match:
            return self.to_int(match.group(1))

        return 0

    def extract_veteran(self, text: str) -> int:

        matches = re.findall(
            r"Veteran\s*([\d,]+)",
            text,
            re.IGNORECASE,
        )

        if matches:
            return self.to_int(matches[0])

        return 0

    def extract_hardmode(self, text: str) -> int:

        match = re.search(
            r"Veteran\s*([\d,]+)\s*\(Hard Mode\)",
            text,
            re.IGNORECASE,
        )

        if match:
            return self.to_int(match.group(1))

        return 0

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def to_int(value: str) -> int:

        return int(value.replace(",", ""))