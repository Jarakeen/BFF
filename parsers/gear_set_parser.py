# ==================================================
# Black Feather Foundry
#
# File:
# parsers/gear_sets_parser.py
#
# Purpose:
# Convert the raw ESO item dump into canonical
# gear-set records.
#
# The raw item dump contains one record for every
# individual item. This parser collapses those
# records into ONE record per setId.
#
# Responsibilities:
# - Group items by setId
# - Extract set identity
# - Extract set bonuses
# - Collect available equipment pieces
# - Collect armor weights
# - Collect weapon types
# - Track source item IDs
# - Classify Monster Sets
# - Validate the resulting records
#
# This parser does NOT:
# - Interpret combat capabilities
# - Determine buffs/debuffs
# - Optimize builds
# - Determine raid requirements
#
# ==================================================

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
import json


class GearSetParser:
    """
    Builds canonical gear-set records from the
    raw ESO mined-item dataset.
    """

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    def __init__(
        self,
        raw_file: str | Path,
        output_file: str | Path,
    ):
        self.raw_file = Path(raw_file)
        self.output_file = Path(output_file)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def parse(self) -> dict[str, dict]:
        """
        Parse the raw item file and return one
        canonical record per set.
        """

        records = self._load_raw_items()

        grouped = self._group_by_set(records)

        sets = {}

        for set_id, items in grouped.items():

            record = self._build_set(
                set_id,
                items,
            )

            if record is None:
                continue

            sets[str(set_id)] = record

        return sets

    def run(self) -> dict[str, dict]:
        """
        Parse the raw data and write the resulting
        canonical gear-set database to disk.
        """

        sets = self.parse()

        self._write_output(sets)

        return sets

    # --------------------------------------------------
    # Loading
    # --------------------------------------------------

    def _load_raw_items(self) -> list[dict]:
        """
        Load the UESP DumpMinedItems JSON structure.

        Expected structure:

        {
            "numRecords": 60145,
            "minedItemSummary": [
                {...},
                {...},
                ...
            ]
        }
        """

        if not self.raw_file.exists():
            raise FileNotFoundError(
                f"Raw item file not found: "
                f"{self.raw_file}"
            )

        with self.raw_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Expected gear set data to be "
                "a JSON object."
            )

        records = data.get(
            "minedItemSummary"
        )

        if not isinstance(records, list):
            raise ValueError(
                "gear_sets_raw.json does not contain "
                "a valid 'minedItemSummary' list."
            )

        if not records:
            raise ValueError(
                "minedItemSummary is empty."
            )

        return records
    # --------------------------------------------------
    # Grouping
    # --------------------------------------------------

    def _group_by_set(
        self,
        records: list[dict],
    ) -> dict[str, list[dict]]:
        """
        Group raw item records by setId.
        """

        groups: dict[str, list[dict]] = defaultdict(
            list
        )

        for record in records:

            set_id = self._int_value(
                record.get("setId")
            )

            # -1 and missing means the item does
            # not belong to a gear set.

            if set_id is None:
                continue

            if set_id <= 0:
                continue

            groups[str(set_id)].append(
                record
            )

        return dict(groups)

    # --------------------------------------------------
    # Set Builder
    # --------------------------------------------------

    def _build_set(
        self,
        set_id: str,
        items: list[dict],
    ) -> dict | None:
        """
        Build one canonical set from all raw
        item records belonging to that set.
        """

        if not items:
            return None

        representative = self._choose_representative(
            items
        )

        name = self._clean_string(
            representative.get("setName")
        )

        if not name:
            name = self._find_first_value(
                items,
                "setName",
            )

        if not name:
            return None

        pieces = self._collect_pieces(
            items
        )

        bonuses = self._collect_bonuses(
            items
        )

        max_equip_count = self._find_max_equip_count(
            items
        )

        category = self._classify_set(
            pieces
        )

        return {
            "id": int(set_id),

            "name": name,

            "category": category,

            "max_equip_count": max_equip_count,

            "pieces": pieces,

            "bonuses": bonuses,

            "source_item_ids": self._collect_item_ids(
                items
            ),

            "source": {
                "item_count": len(items),
            },
        }

    # --------------------------------------------------
    # Representative Record
    # --------------------------------------------------

    @staticmethod
    def _choose_representative(
        items: list[dict],
    ) -> dict:
        """
        Choose a representative item.

        Set metadata is repeated across the raw
        item records, so one representative is
        sufficient for set-level fields.
        """

        for item in items:

            if item.get("setName"):
                return item

        return items[0]

    # --------------------------------------------------
    # Pieces
    # --------------------------------------------------

    def _collect_pieces(
        self,
        items: list[dict],
    ) -> dict:
        """
        Collect the equipment characteristics
        available for the set.

        Individual items are deduplicated into
        structural information.
        """

        slots = set()
        armor_types = set()
        weapon_types = set()
        craft_types = set()

        item_records = []

        for item in items:

            item_id = self._int_value(
                item.get("itemId")
            )

            equip_type = self._int_value(
                item.get("equipType")
            )

            armor_type = self._int_value(
                item.get("armorType")
            )

            weapon_type = self._int_value(
                item.get("weaponType")
            )

            craft_type = self._int_value(
                item.get("craftType")
            )

            if equip_type is not None:
                slots.add(
                    equip_type
                )

            if armor_type is not None and armor_type > 0:
                armor_types.add(
                    armor_type
                )

            if weapon_type is not None and weapon_type > 0:
                weapon_types.add(
                    weapon_type
                )

            if craft_type is not None and craft_type > 0:
                craft_types.add(
                    craft_type
                )

            if item_id is not None:

                item_records.append(
                    {
                        "item_id": item_id,
                        "equip_type": equip_type,
                        "armor_type": armor_type,
                        "weapon_type": weapon_type,
                    }
                )

        return {
            "equip_types": sorted(
                slots
            ),

            "armor_types": sorted(
                armor_types
            ),

            "weapon_types": sorted(
                weapon_types
            ),

            "craft_types": sorted(
                craft_types
            ),

            "items": item_records,
        }

    # --------------------------------------------------
    # Bonuses
    # --------------------------------------------------

    def _collect_bonuses(
        self,
        items: list[dict],
    ) -> dict[str, str]:
        """
        Extract set bonus descriptions.

        The same set bonus information is repeated
        across the individual item records, so the
        first valid occurrence for each piece count
        is retained.
        """

        bonuses: dict[str, str] = {}

        for item in items:

            for index in range(
                1,
                13,
            ):

                count = self._int_value(
                    item.get(
                        f"setBonusCount{index}"
                    )
                )

                description = self._clean_string(
                    item.get(
                        f"setBonusDesc{index}"
                    )
                )

                if count is None:
                    continue

                if count <= 0:
                    continue

                if not description:
                    continue

                key = str(count)

                if key not in bonuses:

                    bonuses[key] = description

        return dict(
            sorted(
                bonuses.items(),
                key=lambda pair: int(pair[0]),
            )
        )

    # --------------------------------------------------
    # Max Equip Count
    # --------------------------------------------------

    def _find_max_equip_count(
        self,
        items: list[dict],
    ) -> int | None:
        """
        Determine the maximum set count.
        """

        values = []

        for item in items:

            value = self._int_value(
                item.get(
                    "setMaxEquipCount"
                )
            )

            if value is not None and value > 0:

                values.append(
                    value
                )

        if not values:
            return None

        return max(values)

    # --------------------------------------------------
    # Item IDs
    # --------------------------------------------------

    def _collect_item_ids(
        self,
        items: list[dict],
    ) -> list[int]:
        """
        Collect unique raw item IDs belonging
        to this set.
        """

        ids = set()

        for item in items:

            item_id = self._int_value(
                item.get("itemId")
            )

            if item_id is not None:
                ids.add(item_id)

        return sorted(ids)

    # --------------------------------------------------
    # Classification
    # --------------------------------------------------

    def _classify_set(
        self,
        pieces: dict,
    ) -> str:
        """
        Classify the set based on its available
        equipment structure.

        Current rule:

        Head + Shoulders only
            -> Monster Set

        Everything else
            -> Standard

        The exact equipType mapping should be
        confirmed against the UESP documentation
        before relying on this classification
        in production.
        """

        equip_types = set(
            pieces.get(
                "equip_types",
                [],
            )
        )

        if self._is_head_shoulders_only(
            equip_types
        ):
            return "monster"

        return "standard"

    # --------------------------------------------------
    # Monster Set Detection
    # --------------------------------------------------

    def _is_head_shoulders_only(
        self,
        equip_types: set[int],
    ) -> bool:
        """
        Determine whether a set contains only
        head and shoulders.

        IMPORTANT:
        The equipType IDs are intentionally kept
        in one place so they can be corrected
        against the UESP DumpMinedItems
        documentation without changing the
        rest of the parser.
        """

        # TODO:
        # Replace these IDs with the documented
        # UESP equipType values once confirmed.

        HEAD_EQUIP_TYPE = 3
        SHOULDERS_EQUIP_TYPE = 4

        return equip_types == {
            HEAD_EQUIP_TYPE,
            SHOULDERS_EQUIP_TYPE,
        }

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    @staticmethod
    def _clean_string(
        value: Any,
    ) -> str | None:
        """
        Normalize a string value.
        """

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        return value

    @staticmethod
    def _int_value(
        value: Any,
    ) -> int | None:
        """
        Convert a raw value to int.

        ESO dumps frequently use strings such
        as "49" and "-1".
        """

        if value is None:
            return None

        try:
            return int(
                str(value).strip()
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _find_first_value(
        items: list[dict],
        field: str,
    ) -> str | None:
        """
        Find the first non-empty value for
        a field.
        """

        for item in items:

            value = item.get(field)

            value = (
                str(value).strip()
                if value is not None
                else ""
            )

            if value:
                return value

        return None

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(
        self,
        sets: dict[str, dict],
    ) -> list[str]:
        """
        Validate the canonical set collection.

        Returns a list of warning/error messages.
        """

        problems = []

        seen_ids = set()

        for key, record in sets.items():

            set_id = record.get("id")

            if set_id in seen_ids:

                problems.append(
                    f"Duplicate set ID: {set_id}"
                )

            seen_ids.add(set_id)

            if not record.get("name"):

                problems.append(
                    f"Set {set_id} has no name."
                )

            if not record.get("pieces"):

                problems.append(
                    f"Set {set_id} has no pieces."
                )

            if not record.get("bonuses"):

                problems.append(
                    f"Set {set_id} has no bonuses: "
                    f"{record.get('name')}"
                )

        return problems

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    def _write_output(
        self,
        sets: dict[str, dict],
    ) -> None:
        """
        Write canonical gear-set data.

        This JSON output is currently a derived
        artifact for inspection/debugging.

        SQLite persistence should be connected
        through the Foundry Database layer.
        """

        self.output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.output_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                sets,
                file,
                indent=2,
                ensure_ascii=False,
            )