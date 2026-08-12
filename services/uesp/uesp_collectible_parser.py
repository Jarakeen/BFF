from __future__ import annotations

import re
from dataclasses import dataclass, field

from services.uesp.uesp_client import UespPage


@dataclass
class UespCollectible:
    title: str
    page_id: int
    revision_id: int

    collectible_id: int | None = None
    collectible_type: str = ""
    type: str = ""

    name: str = ""
    description: str = ""
    icon: str = ""
    image: str = ""
    image_description: str = ""

    acquisition: str = ""
    crate: str = ""
    tier: str = ""
    price: str = ""
    date: str = ""

    categories: list[str] = field(default_factory=list)


class UespCollectibleParser:

    TEMPLATE = "Online Collectible Summary"

    def parse(self, page: UespPage) -> UespCollectible:

        fields = self._extract_template(page.wikitext)

        collectible_id = self._int_or_none(
            fields.get("id", "")
        )

        return UespCollectible(
            title=page.title,
            page_id=page.page_id,
            revision_id=page.revision_id,

            collectible_id=collectible_id,
            collectible_type=fields.get(
                "collectibletype", ""
            ),
            type=fields.get(
                "type", ""
            ),

            name=fields.get(
                "name", ""
            ) or page.title.removeprefix("Online:"),

            description=fields.get(
                "description", ""
            ),

            icon=fields.get(
                "icon", ""
            ),

            image=fields.get(
                "image", ""
            ),

            image_description=fields.get(
                "imgdesc", ""
            ),

            acquisition=fields.get(
                "acquisition", ""
            ),

            crate=fields.get(
                "crate", ""
            ),

            tier=fields.get(
                "tier", ""
            ),

            price=fields.get(
                "price", ""
            ),

            date=fields.get(
                "date", ""
            ),

            categories=page.categories,
        )

    def _extract_template(
        self,
        wikitext: str,
    ) -> dict[str, str]:

        pattern = re.compile(
            r"\{\{\s*"
            + re.escape(self.TEMPLATE)
            + r"\s*(.*?)\}\}",
            re.DOTALL | re.IGNORECASE,
        )

        match = pattern.search(wikitext)

        if not match:
            return {}

        fields: dict[str, str] = {}

        for line in match.group(1).splitlines():

            line = line.strip()

            if not line.startswith("|"):
                continue

            line = line[1:]

            if "=" not in line:
                continue

            key, value = line.split(
                "=",
                1,
            )

            fields[key.strip().lower()] = (
                value.strip()
            )

        return fields

    @staticmethod
    def _int_or_none(
        value: str,
    ) -> int | None:

        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None