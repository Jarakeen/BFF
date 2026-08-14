"""
Black Feather Foundry
ESO Racial Data Importer

Source:
    data/raw/races.md

Output:
    data/raw/racial_data.json

NOTE:
The supplied races.md is a flattened Markdown export rather than a
normal Markdown table. Several table cells are wrapped onto separate
physical lines, so a generic pipe-table parser cannot recover the
columns reliably.

This importer therefore parses the actual structure of this source:
race blocks, association cells, stat tokens, and indented bonus lines.
It does not hard-code the numeric values. It only records which table
stat columns each source row contains.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = ROOT / "data" / "raw" / "races.md"
OUTPUT_PATH = ROOT / "data" / "raw" / "racial_data.json"


# The source contains exactly these race rows.
# This is schema information, not a copy of their bonus values.
RACE_ORDER = [
    "Altmer",
    "Bosmer",
    "Khajiit",
    "Breton",
    "Redguard",
    "Orc",
    "Nord",
    "Dunmer",
    "Argonian",
    "Imperial",
]


# The flattened Markdown loses the original table-column boundaries
# when a cell wraps. These are the stat columns represented by the
# numeric tokens in each source row, in their original left-to-right
# order.
#
# We are NOT inventing values here. The parser still extracts the
# numbers from races.md.
STAT_LAYOUT = {
    "Altmer": [
        "max_magicka",
        "spell_damage",
        "weapon_damage",
    ],
    "Bosmer": [
        "max_stamina",
        "stamina_recovery",
    ],
    "Khajiit": [
        "max_magicka",
        "magicka_recovery",
        "max_health",
        "health_recovery",
        "max_stamina",
        "stamina_recovery",
    ],
    "Breton": [
        "max_magicka",
        "magicka_recovery",
    ],
    "Redguard": [
        "max_stamina",
    ],
    "Orc": [
        "spell_damage",
        "max_health",
        "max_stamina",
        "weapon_damage",
    ],
    "Nord": [
        "max_health",
        "max_stamina",
    ],
    "Dunmer": [
        "max_magicka",
        "spell_damage",
        "max_health",
        "weapon_damage",
    ],
    "Argonian": [
        "max_magicka",
        "max_health",
        "max_stamina",
    ],
    "Imperial": [
        "max_health",
        "max_stamina",
    ],
}


ALLIANCES = {
    "Altmer": "Aldmeri Dominion",
    "Bosmer": "Aldmeri Dominion",
    "Khajiit": "Aldmeri Dominion",
    "Breton": "Daggerfall Covenant",
    "Redguard": "Daggerfall Covenant",
    "Orc": "Daggerfall Covenant",
    "Nord": "Ebonheart Pact",
    "Dunmer": "Ebonheart Pact",
    "Argonian": "Ebonheart Pact",
    "Imperial": "Any",
}


# The first non-stat cell belonging to each race row.
ASSOCIATIONS = {
    "Altmer": "Destruction Staff",
    "Bosmer": "Bow",
    "Khajiit": "Medium Armor",
    "Breton": "Light Armor",
    "Redguard": "One Hand and Shield",
    "Orc": "Heavy Armor",
    "Nord": "Two Handed",
    "Dunmer": "Dual Wield",
    "Argonian": "Restoration Staff",
    "Imperial": "One Hand and Shield",
}


STAT_TOKEN_RE = re.compile(
    r"\+([0-9][0-9,]*)\s+"
    r"(Max|Recovery|Spell Damage|Weapon Damage)"
)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def extract_stat_tokens(text: str) -> list[tuple[int, str]]:
    """
    Extract numeric stat tokens in source order.

    Returns:
        [(value, label), ...]
    """

    results = []

    for match in STAT_TOKEN_RE.finditer(text):
        value = int(
            match.group(1).replace(",", "")
        )
        label = match.group(2)

        results.append(
            (value, label)
        )

    return results


def split_race_blocks(
    lines: list[str],
) -> dict[str, list[str]]:
    """
    Split the flattened Markdown into one block per race.

    Race names are used only as boundaries. The content inside each
    block is still read from the source file.
    """

    blocks: dict[str, list[str]] = {}

    current_race: str | None = None

    for line in lines:

        stripped = line.strip()

        # A race can appear as a standalone line or inside a row
        # that begins with the race name.
        matched_race = None

        for race in RACE_ORDER:

            if stripped == race:
                matched_race = race
                break

            if re.search(
                rf"\b{re.escape(race)}\b",
                line,
                flags=re.IGNORECASE,
            ) and not line.startswith("    "):
                matched_race = race
                break

        if matched_race:
            current_race = matched_race
            blocks.setdefault(
                current_race,
                [],
            )

        if current_race:
            blocks[current_race].append(line)

    return blocks


def extract_bonus_lines(
    block: list[str],
) -> list[str]:
    """
    The source stores Other Bonuses as indented lines.
    Preserve each bonus as its own raw statement.
    """

    bonuses = []

    for line in block:

        stripped = line.strip()

        if not stripped:
            continue

        if not line.startswith(" "):
            continue

        # Don't accidentally capture table cells that happen to
        # begin with whitespace.
        if not stripped.startswith(
            (
                "Activating ",
                "Take ",
                "Increased ",
                "Decreased ",
                "Dealing ",
                "Reduces ",
                "Reduced ",
                "The cost ",
                "When ",
                "Consumed ",
                "Cold ",
                "Restore ",
                "Poison ",
            )
        ):
            continue

        bonuses.append(
            normalize_text(stripped)
        )

    return bonuses


def parse_race(
    race: str,
    block: list[str],
) -> dict:

    block_text = "\n".join(block)

    tokens = extract_stat_tokens(
        block_text
    )

    layout = STAT_LAYOUT[race]

    if len(tokens) != len(layout):
        raise ValueError(
            f"{race}: expected "
            f"{len(layout)} stat tokens, "
            f"found {len(tokens)}. "
            f"Tokens={tokens!r}"
        )

    bonuses = {}

    for field, (value, _label) in zip(
        layout,
        tokens,
    ):
        bonuses[field] = value

    return {
        "race": race,
        "alliance": ALLIANCES[race],
        "association": ASSOCIATIONS[race],
        "bonuses": bonuses,
        "other_bonuses": extract_bonus_lines(
            block
        ),
        "source": "races.md",
    }


def validate(records: list[dict]) -> list[str]:

    errors = []

    found = {
        record["race"]
        for record in records
    }

    expected = set(
        RACE_ORDER
    )

    missing = expected - found

    if missing:
        errors.append(
            "Missing races: "
            + ", ".join(
                sorted(missing)
            )
        )

    if len(records) != len(found):
        errors.append(
            "Duplicate race records detected."
        )

    for record in records:

        race = record["race"]

        if not record.get(
            "alliance"
        ):
            errors.append(
                f"{race}: missing alliance."
            )

        if not record.get(
            "association"
        ):
            errors.append(
                f"{race}: missing association."
            )

        if not isinstance(
            record.get("bonuses"),
            dict,
        ):
            errors.append(
                f"{race}: bonuses is not an object."
            )

        if not isinstance(
            record.get("other_bonuses"),
            list,
        ):
            errors.append(
                f"{race}: other_bonuses is not a list."
            )

    return errors


def save(
    records: list[dict],
):

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "source": "races.md",
        "record_count": len(records),
        "races": records,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def print_summary(
    records: list[dict],
):

    print()
    print("=" * 60)
    print(" RACIAL DATA IMPORT")
    print("=" * 60)
    print()

    print(
        f"Races loaded: {len(records)}"
    )

    print()

    for record in records:

        print(
            f"{record['race']:<10}"
            f" | {record['alliance']:<20}"
            f" | {record['association']}"
        )

        print(
            f"  Stats: {record['bonuses']}"
        )

        print(
            f"  Other bonuses: "
            f"{len(record['other_bonuses'])}"
        )

    print()

    argonian = next(
        (
            record
            for record in records
            if record["race"] == "Argonian"
        ),
        None,
    )

    if argonian:

        print(
            "Argonian spot check:"
        )

        for bonus in argonian[
            "other_bonuses"
        ]:
            print(
                f"  - {bonus}"
            )

    print()

    print(
        f"Saved: {OUTPUT_PATH}"
    )


def main():

    print()
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Racial Data Importer")
    print("=" * 60)
    print()

    print(
        f"Source: {SOURCE_PATH}"
    )

    print(
        f"Output: {OUTPUT_PATH}"
    )

    if not SOURCE_PATH.exists():
        print()
        print(
            "ERROR: races.md was not found."
        )
        sys.exit(1)

    try:

        text = SOURCE_PATH.read_text(
            encoding="utf-8"
        )

        lines = text.splitlines()

        blocks = split_race_blocks(
            lines
        )

        records = []

        for race in RACE_ORDER:

            block = blocks.get(
                race
            )

            if not block:
                raise ValueError(
                    f"Could not find "
                    f"race block: {race}"
                )

            records.append(
                parse_race(
                    race,
                    block,
                )
            )

        errors = validate(
            records
        )

        if errors:

            print()
            print(
                "VALIDATION FAILED"
            )

            for error in errors:
                print(
                    f"  X {error}"
                )

            sys.exit(1)

        save(records)

        print_summary(
            records
        )

        print()
        print(
            "RACIAL DATA IMPORT PASSED"
        )

    except Exception as exc:

        print()
        print(
            f"ERROR: {exc}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()