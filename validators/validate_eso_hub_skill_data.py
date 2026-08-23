"""
Black Feather Foundry
ESO-Hub Skill Data Validator

Validates the raw dataset produced by:
    importers/eso_hub_skill_crawler_v2.py

Checks:
    - JSON structure
    - required fields
    - record types
    - duplicate URLs / names
    - malformed relationship entries
    - invalid URLs
    - CP condition preservation
    - category counts
    - known ESO-Hub spot checks

This validator does NOT assume ESO-Hub lists every possible
in-game relationship. It validates what our crawler captured.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = (
    ROOT
    / "data"
    / "raw"
    / "eso_hub_skill_data.json"
)


# ============================================================
# EXPECTED SCHEMA
# ============================================================

REQUIRED_FIELDS = {
    "skill_name",
    "eso_hub_url",
    "weapon",
    "buffs",
    "debuffs",
    "status_effects",
    "modifying_sets",
    "champion_points",
    "source",
}

RELATIONSHIP_FIELDS = (
    "weapon",
    "buffs",
    "debuffs",
    "status_effects",
    "modifying_sets",
    "champion_points",
)


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value) -> str:
    if value is None:
        return ""

    value = str(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_name(value) -> str:
    value = normalize_text(value).lower()
    value = value.replace("’", "'")
    value = re.sub(r"[^a-z0-9']+", " ", value)

    return re.sub(r"\s+", " ", value).strip()


def valid_http_url(value) -> bool:
    if not isinstance(value, str):
        return False

    try:
        parsed = urlparse(value)

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )

    except Exception:
        return False


def find_skill(
    skills: list[dict],
    target: str,
) -> dict | None:

    wanted = normalize_name(target)

    for skill in skills:
        name = normalize_name(
            skill.get("skill_name")
        )

        if name == wanted:
            return skill

        # ESO-Hub sometimes includes "Skill - ESO".
        if name.startswith(wanted + " skill"):
            return skill

        if wanted in name:
            return skill

    return None


# ============================================================
# VALIDATOR
# ============================================================

# ============================================================
# KNOWN PAGE SPOT CHECKS
# ============================================================
#
# Structural sanity checks based on the ESO-Hub pages we inspected
# while building the crawler. Exposed at module level (rather than as
# a local literal inside run_spot_checks) so this authoritative,
# human-verified data can be consumed directly by other code -
# e.g. minmax.character_build tests that need a real, sourced fact
# about a specific ability instead of a synthetic fixture.

KNOWN_PAGE_SPOT_CHECKS: list[tuple[str, dict]] = [
    (
        "Aggressive Horn",
        {
            "buffs": ["Major Force"],
            "status_effects": ["Overcharged"],
        },
    ),
    (
        "Caltrops",
        {
            "status_effects": ["Sundered"],
        },
    ),
    (
        "Pierce Armor",
        {
            "debuffs": [
                "Major Breach",
                "Minor Breach",
            ],
            "status_effects": ["Sundered"],
            "modifying_sets": [
                "Perfected Puncturing Remedy",
                "Puncturing Remedy",
            ],
            "champion_points": 9,
        },
    ),
    (
        "Wall of Elements",
        {
            "status_effects": [
                "Chilled",
                "Overcharged",
            ],
        },
    ),
]



# ============================================================
# KNOWN PAGE SPOT CHECKS
# ============================================================
#
# Structural sanity checks based on the ESO-Hub pages we inspected
# while building the crawler. Extracted to a module-level constant
# (rather than a local literal inside run_spot_checks) so this
# authoritative, hand-verified data can be imported and reused by
# other code - e.g. minmax/character_build tests that need a real,
# non-synthetic source fact instead of a fabricated fixture.
#
# Display names here match ESO-Hub's own casing. Consumers that need
# the project's snake_case effect identity (e.g. "major_force") are
# responsible for that conversion - this constant preserves the
# names exactly as ESO-Hub presents them.
KNOWN_PAGE_SPOT_CHECKS: list[tuple[str, dict]] = [
    (
        "Aggressive Horn",
        {
            "buffs": ["Major Force"],
            "status_effects": ["Overcharged"],
        },
    ),
    (
        "Caltrops",
        {
            "status_effects": ["Sundered"],
        },
    ),
    (
        "Pierce Armor",
        {
            "debuffs": [
                "Major Breach",
                "Minor Breach",
            ],
            "status_effects": ["Sundered"],
            "modifying_sets": [
                "Perfected Puncturing Remedy",
                "Puncturing Remedy",
            ],
            "champion_points": 9,
        },
    ),
    (
        "Wall of Elements",
        {
            "status_effects": [
                "Chilled",
                "Overcharged",
            ],
        },
    ),
]


class ESOHubSkillDataValidator:

    def __init__(
        self,
        source_path: Path = SOURCE_PATH,
    ):
        self.source_path = source_path

        self.skills: list[dict] = []

        self.errors: list[str] = []
        self.warnings: list[str] = []

        self.stats = {
            "skills": 0,

            "with_weapon": 0,
            "with_buffs": 0,
            "with_debuffs": 0,
            "with_status_effects": 0,
            "with_modifying_sets": 0,
            "with_champion_points": 0,

            "weapon_relationships": 0,
            "buff_relationships": 0,
            "debuff_relationships": 0,
            "status_relationships": 0,
            "set_relationships": 0,
            "cp_relationships": 0,

            "cp_conditions": 0,

            "valid_urls": 0,
            "invalid_urls": 0,

            "duplicate_names": 0,
            "duplicate_urls": 0,

            "malformed_records": 0,
            "malformed_relationships": 0,
        }

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    def load(self) -> bool:

        print(
            f"Source: {self.source_path}"
        )

        if not self.source_path.exists():
            self.errors.append(
                "Source JSON does not exist."
            )
            return False

        try:
            data = json.loads(
                self.source_path.read_text(
                    encoding="utf-8"
                )
            )

        except json.JSONDecodeError as exc:
            self.errors.append(
                f"Invalid JSON: {exc}"
            )
            return False

        except OSError as exc:
            self.errors.append(
                f"Could not read source: {exc}"
            )
            return False

        if isinstance(data, dict):
            skills = data.get("skills")

            if skills is None:
                self.errors.append(
                    "JSON object does not contain "
                    "'skills'."
                )
                return False

        elif isinstance(data, list):
            # Support older raw-list output.
            skills = data

        else:
            self.errors.append(
                "Top-level JSON must be an object "
                "or list."
            )
            return False

        if not isinstance(skills, list):
            self.errors.append(
                "'skills' must be a list."
            )
            return False

        self.skills = skills
        self.stats["skills"] = len(skills)

        return True

    # --------------------------------------------------------
    # RECORD VALIDATION
    # --------------------------------------------------------

    def validate_record(
        self,
        index: int,
        skill: object,
    ):

        if not isinstance(skill, dict):
            self.stats["malformed_records"] += 1
            self.errors.append(
                f"Record {index}: not an object."
            )
            return

        missing = REQUIRED_FIELDS - set(
            skill.keys()
        )

        if missing:
            self.stats["malformed_records"] += 1
            self.errors.append(
                f"Record {index}: missing fields: "
                f"{', '.join(sorted(missing))}"
            )

        name = skill.get("skill_name")
        url = skill.get("eso_hub_url")

        if not isinstance(name, str) or not name.strip():
            self.stats["malformed_records"] += 1
            self.errors.append(
                f"Record {index}: invalid skill_name."
            )

        if not valid_http_url(url):
            self.stats["invalid_urls"] += 1
            self.errors.append(
                f"Record {index}: invalid skill URL: "
                f"{url!r}"
            )
        else:
            self.stats["valid_urls"] += 1

        for field in RELATIONSHIP_FIELDS:

            value = skill.get(field)

            if value is None:
                self.stats["malformed_relationships"] += 1
                self.errors.append(
                    f"Record {index} "
                    f"{name!r}: {field} is missing."
                )
                continue

            if not isinstance(value, list):
                self.stats["malformed_relationships"] += 1
                self.errors.append(
                    f"Record {index} "
                    f"{name!r}: {field} is not a list."
                )
                continue

            if field == "weapon":
                self.validate_weapon_relationships(
                    index,
                    name,
                    value,
                )
            else:
                self.validate_relationships(
                    index,
                    name,
                    field,
                    value,
                )

    # --------------------------------------------------------
    # RELATIONSHIPS
    # --------------------------------------------------------

    def validate_relationships(
        self,
        index: int,
        skill_name: str,
        field: str,
        values: list,
    ):

        if values:
            count_key = {
                "weapon": "with_weapon",
                "buffs": "with_buffs",
                "debuffs": "with_debuffs",
                "status_effects": "with_status_effects",
                "modifying_sets": "with_modifying_sets",
                "champion_points": "with_champion_points",
            }[field]

            relationship_key = {
                "weapon": "weapon_relationships",
                "buffs": "buff_relationships",
                "debuffs": "debuff_relationships",
                "status_effects": "status_relationships",
                "modifying_sets": "set_relationships",
                "champion_points": "cp_relationships",
            }[field]

            self.stats[count_key] += 1
            self.stats[relationship_key] += len(values)

        seen = set()

        for rel_index, value in enumerate(values):

            if not isinstance(value, dict):
                self.stats["malformed_relationships"] += 1
                self.errors.append(
                    f"{skill_name!r} / {field} "
                    f"[{rel_index}]: expected object, "
                    f"got {type(value).__name__}."
                )
                continue

            name = value.get("name")

            if not isinstance(name, str) or not name.strip():
                self.stats["malformed_relationships"] += 1
                self.errors.append(
                    f"{skill_name!r} / {field} "
                    f"[{rel_index}]: missing name."
                )
                continue

            normalized = normalize_name(name)

            if normalized in seen:
                self.warnings.append(
                    f"{skill_name!r} / {field}: "
                    f"duplicate relationship {name!r}."
                )

            seen.add(normalized)

            source = value.get("source")

            if source != "ESO-Hub":
                self.warnings.append(
                    f"{skill_name!r} / {field} / "
                    f"{name!r}: unexpected source "
                    f"{source!r}."
                )

            url = value.get("url")

            if url is not None and not valid_http_url(url):
                self.stats["invalid_urls"] += 1
                self.errors.append(
                    f"{skill_name!r} / {field} / "
                    f"{name!r}: invalid URL."
                )

            if field == "champion_points":
                condition = value.get("condition")

                if condition:
                    self.stats["cp_conditions"] += 1


    def validate_weapon_relationships(
        self,
        index,
        skill_name,
        relationships,
    ):
        for item_index, relationship in enumerate(
            relationships
        ):

            if not isinstance(
                relationship,
                dict,
            ):
                self.stats[
                    "malformed_relationships"
                ] += 1

                self.errors.append(
                    f"Record {index} "
                    f"{skill_name!r}: "
                    f"weapon [{item_index}] "
                    f"is not an object."
                )

                continue

            required_fields = (
                "category",
                "category_url",
                "skill_line",
                "skill_line_url",
            )

            for field in required_fields:

                value = relationship.get(field)

                if (
                    not isinstance(value, str)
                    or not value.strip()
                ):
                    self.stats[
                        "malformed_relationships"
                    ] += 1

                    self.errors.append(
                        f"Record {index} "
                        f"{skill_name!r}: "
                        f"weapon [{item_index}] "
                        f"missing {field}."
                    )
                    
    # --------------------------------------------------------
    # DUPLICATES
    # --------------------------------------------------------

    def validate_duplicates(self):

        names = {}
        urls = {}

        for index, skill in enumerate(
            self.skills,
            1,
        ):

            if not isinstance(skill, dict):
                continue

            name = normalize_name(
                skill.get("skill_name")
            )

            url = normalize_text(
                skill.get("eso_hub_url")
            )

            if name:
                names.setdefault(
                    name,
                    [],
                ).append(index)

            if url:
                urls.setdefault(
                    url,
                    [],
                ).append(index)

        duplicate_names = {
            key: indexes
            for key, indexes in names.items()
            if len(indexes) > 1
        }

        duplicate_urls = {
            key: indexes
            for key, indexes in urls.items()
            if len(indexes) > 1
        }

        self.stats["duplicate_names"] = len(
            duplicate_names
        )

        self.stats["duplicate_urls"] = len(
            duplicate_urls
        )

        for name, indexes in duplicate_names.items():
            self.warnings.append(
                f"Duplicate skill name: "
                f"{name!r} at records "
                f"{indexes}"
            )

        for url, indexes in duplicate_urls.items():
            self.errors.append(
                f"Duplicate skill URL at records "
                f"{indexes}: {url}"
            )

    # --------------------------------------------------------
    # KNOWN SPOT CHECKS
    # --------------------------------------------------------

    def spot_check(
        self,
        target: str,
        expected: dict,
    ) -> bool:

        skill = find_skill(
            self.skills,
            target,
        )

        if skill is None:
            self.warnings.append(
                f"Spot check: {target!r} "
                f"was not found."
            )
            return False

        passed = True

        for field, expected_value in expected.items():

            actual = skill.get(field)

            if isinstance(expected_value, list):
                actual_names = [
                    normalize_name(
                        item.get("name")
                    )
                    for item in actual
                    if isinstance(item, dict)
                ]

                expected_names = [
                    normalize_name(name)
                    for name in expected_value
                ]

                for wanted in expected_names:
                    if wanted not in actual_names:
                        self.errors.append(
                            f"Spot check failed: "
                            f"{target} / {field} "
                            f"missing {wanted!r}."
                        )
                        passed = False

            elif isinstance(expected_value, int):
                actual_count = (
                    len(actual)
                    if isinstance(actual, list)
                    else -1
                )

                if actual_count != expected_value:
                    self.errors.append(
                        f"Spot check failed: "
                        f"{target} / {field}: "
                        f"expected {expected_value}, "
                        f"got {actual_count}."
                    )
                    passed = False

        return passed

    def run_spot_checks(self):

        print()
        print("=" * 60)
        print(" KNOWN PAGE SPOT CHECKS")
        print("=" * 60)

        # These are structural sanity checks based on the
        # ESO-Hub pages we inspected while building the crawler.

        checks = KNOWN_PAGE_SPOT_CHECKS

        for target, expected in checks:

            skill = find_skill(
                self.skills,
                target,
            )

            if skill is None:
                print(
                    f"  WARNING: {target} not found"
                )
                continue

            passed = self.spot_check(
                target,
                expected,
            )

            if passed:
                print(
                    f"  PASS: {target}"
                )
            else:
                print(
                    f"  FAIL: {target}"
                )

    # --------------------------------------------------------
    # SUSPICIOUS GLOBAL CONDITIONS
    # --------------------------------------------------------

    def global_warnings(self):

        if not self.skills:
            self.errors.append(
                "Dataset contains zero skills."
            )
            return

        if self.stats["with_buffs"] == 0:
            self.warnings.append(
                "Buffs are empty for every skill."
            )

        if self.stats["with_debuffs"] == 0:
            self.warnings.append(
                "Debuffs are empty for every skill."
            )

        if self.stats["with_status_effects"] == 0:
            self.warnings.append(
                "Status effects are empty for "
                "every skill."
            )

        if self.stats["with_modifying_sets"] == 0:
            self.warnings.append(
                "Modifying armor sets are empty "
                "for every skill."
            )

        if self.stats["with_champion_points"] == 0:
            self.warnings.append(
                "Champion Points are empty for "
                "every skill."
            )

        if self.stats["invalid_urls"] > 0:
            self.errors.append(
                f"There are "
                f"{self.stats['invalid_urls']} "
                f"invalid URLs."
            )

    # --------------------------------------------------------
    # FULL RUN
    # --------------------------------------------------------

    def run(self) -> bool:

        print()
        print("=" * 60)
        print(" Black Feather Foundry")
        print(" ESO-Hub Skill Data Validator")
        print("=" * 60)
        print()

        if not self.load():
            return False

        for index, skill in enumerate(
            self.skills,
            1,
        ):
            self.validate_record(
                index,
                skill,
            )

        self.validate_duplicates()
        self.global_warnings()
        self.run_spot_checks()

        self.print_summary()

        return not self.errors

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    def print_summary(self):

        print()
        print("=" * 60)
        print(" VALIDATION SUMMARY")
        print("=" * 60)
        print()

        print(
            f"Skills:                 "
            f"{self.stats['skills']}"
        )

        print()
        print("Buffs")
        print(
            f"  With buffs:           "
            f"{self.stats['with_buffs']}"
        )
        print(
            f"  Relationships:        "
            f"{self.stats['buff_relationships']}"
        )

        print()
        print("Debuffs")
        print(
            f"  With debuffs:         "
            f"{self.stats['with_debuffs']}"
        )
        print(
            f"  Relationships:        "
            f"{self.stats['debuff_relationships']}"
        )

        print()
        print("Status Effects")
        print(
            f"  With effects:         "
            f"{self.stats['with_status_effects']}"
        )
        print(
            f"  Relationships:        "
            f"{self.stats['status_relationships']}"
        )

        print()
        print("Modifying Armor Sets")
        print(
            f"  With sets:            "
            f"{self.stats['with_modifying_sets']}"
        )
        print(
            f"  Relationships:        "
            f"{self.stats['set_relationships']}"
        )

        print()
        print("Weapons")
        print(
            f"  With weapon:          "
            f"{self.stats['with_weapon']}"
        )
        print(
            f"  Relationships:        "
            f"{self.stats['weapon_relationships']}"
        )

        print()
        print("Champion Points")
        print(
            f"  With CP:              "
            f"{self.stats['with_champion_points']}"
        )
        print(
            f"  Relationships:        "
            f"{self.stats['cp_relationships']}"
        )
        print(
            f"  Conditions:           "
            f"{self.stats['cp_conditions']}"
        )

        print()
        print("URLs")
        print(
            f"  Valid:                "
            f"{self.stats['valid_urls']}"
        )
        print(
            f"  Invalid:              "
            f"{self.stats['invalid_urls']}"
        )

        print()
        print("Duplicates")
        print(
            f"  Duplicate names:      "
            f"{self.stats['duplicate_names']}"
        )
        print(
            f"  Duplicate URLs:       "
            f"{self.stats['duplicate_urls']}"
        )

        print()
        print(
            f"Malformed records:       "
            f"{self.stats['malformed_records']}"
        )

        print(
            f"Malformed relationships: "
            f"{self.stats['malformed_relationships']}"
        )

        print()

        if self.errors:
            print("=" * 60)
            print(" ERRORS")
            print("=" * 60)

            for error in self.errors:
                print(f"  X {error}")

        if self.warnings:
            print()
            print("=" * 60)
            print(" WARNINGS")
            print("=" * 60)

            for warning in self.warnings:
                print(f"  ! {warning}")

        print()

        if self.errors:
            print(
                "VALIDATION FAILED"
            )
        else:
            print(
                "VALIDATION PASSED"
                + (
                    " WITH WARNINGS"
                    if self.warnings
                    else ""
                )
            )


# ============================================================
# MAIN
# ============================================================

def main():

    validator = ESOHubSkillDataValidator()

    passed = validator.run()

    raise SystemExit(
        0 if passed else 1
    )


if __name__ == "__main__":
    main()