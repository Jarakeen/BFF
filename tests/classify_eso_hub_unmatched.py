import json
import re
import sqlite3
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CROSSWALK_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "eso_hub_skill_crosswalk_v2.json"
)
DB_PATH = BASE_DIR / "data" / "eso.db"
OUTPUT_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "eso_hub_unmatched_classification.json"
)


def normalize(value):
    if not isinstance(value, str):
        return ""

    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def parse_skill_url(url):
    if not isinstance(url, str):
        return {
            "category": "",
            "skill_line": "",
            "slug": "",
            "parts": [],
        }

    marker = "/en/skills/"

    if marker not in url:
        return {
            "category": "",
            "skill_line": "",
            "slug": "",
            "parts": [],
        }

    path = url.split(marker, 1)[1]
    path = path.split("?", 1)[0]
    path = path.split("#", 1)[0]

    parts = [
        part.strip()
        for part in path.split("/")
        if part.strip()
    ]

    return {
        "category": normalize(parts[0])
        if parts else "",
        "skill_line": normalize(parts[-2])
        if len(parts) >= 2 else "",
        "slug": normalize(parts[-1])
        if parts else "",
        "parts": parts,
    }


def classify(record):
    name = record.get("skill_name", "")
    name_norm = normalize(name)

    parsed = parse_skill_url(
        record.get("eso_hub_url")
    )

    url = record.get("eso_hub_url", "").casefold()
    skill_line = parsed["skill_line"]

    # These are deliberately structural classifications.
    # We are not claiming they are missing from the DB yet.

    if "vengeance-" in url or "vengeance/" in url:
        return (
            "vengeance_variant",
            "special_eso_hub_variant",
            "Requires separate Vengeance-family "
            "mapping. Do not import as an ordinary "
            "skill automatically.",
        )

    if "class-mastery" in url:
        return (
            "class_mastery",
            "separate_skill_family",
            "Requires Class Mastery mapping. "
            "Do not force into a normal class "
            "skill line.",
        )

    if "/dawns-wrath/" in url:
        return (
            "skill_line_dawns_wrath",
            "skill_line_mapping",
            "Dawn's Wrath entries are unmatched "
            "despite being ordinary skill records. "
            "Investigate internal skill-line identity.",
        )

    if "/winters-embrace/" in url:
        return (
            "skill_line_winters_embrace",
            "skill_line_mapping",
            "Winter's Embrace entries are unmatched "
            "despite being ordinary skill records. "
            "Investigate internal skill-line identity.",
        )

    if name_norm.endswith(" skill"):
        return (
            "name_variant",
            "name_normalization",
            "Retry matching after removing the "
            "trailing 'Skill' from the ESO-Hub name.",
        )

    return (
        "other",
        "manual_review",
        "No known structural classification.",
    )


def get_name_candidates(db, name):
    rows = db.execute(
        """
        SELECT
            id,
            name,
            skill_line,
            base_ability_id
        FROM skill
        WHERE lower(name) = lower(?)
        ORDER BY id
        """,
        (name,),
    ).fetchall()

    return [
        {
            "skill_id": row[0],
            "name": row[1],
            "skill_line": row[2],
            "base_ability_id": row[3],
        }
        for row in rows
    ]


def get_stripped_skill_candidates(db, name):
    stripped = re.sub(
        r"\s+skill$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()

    if stripped == name.strip():
        return []

    return get_name_candidates(
        db,
        stripped,
    )


def get_ability_candidates(db, name):
    rows = db.execute(
        """
        SELECT
            ability_id,
            name,
            skill_line,
            base_ability_id
        FROM ability
        WHERE lower(name) = lower(?)
        ORDER BY ability_id
        """,
        (name,),
    ).fetchall()

    return [
        {
            "ability_id": row[0],
            "name": row[1],
            "skill_line": row[2],
            "base_ability_id": row[3],
        }
        for row in rows
    ]


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" ESO-Hub Unmatched Classifier")
    print("=" * 60)
    print()
    print("READ-ONLY")
    print()

    if not CROSSWALK_PATH.exists():
        raise FileNotFoundError(
            f"Crosswalk not found:\n{CROSSWALK_PATH}"
        )

    with CROSSWALK_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        crosswalk = json.load(handle)

    unmatched = crosswalk.get(
        "unmatched",
        [],
    )

    if not isinstance(unmatched, list):
        raise ValueError(
            "Crosswalk 'unmatched' must be a list."
        )

    db = sqlite3.connect(DB_PATH)

    classifications = []
    counts = Counter()

    try:
        for item in unmatched:
            record = item.get(
                "record",
                {},
            )

            category, action, explanation = classify(
                record
            )

            name = record.get(
                "skill_name",
                "",
            )

            exact_skill_matches = (
                get_name_candidates(
                    db,
                    name,
                )
            )

            stripped_skill_matches = (
                get_stripped_skill_candidates(
                    db,
                    name,
                )
            )

            ability_matches = (
                get_ability_candidates(
                    db,
                    name,
                )
            )

            entry = {
                "index": item.get("index"),
                "skill_name": name,
                "url": record.get(
                    "eso_hub_url"
                ),
                "category": category,
                "recommended_action": action,
                "explanation": explanation,
                "url_parts": parse_skill_url(
                    record.get(
                        "eso_hub_url"
                    )
                ),
                "database_evidence": {
                    "exact_skill_matches":
                        exact_skill_matches,
                    "stripped_skill_matches":
                        stripped_skill_matches,
                    "exact_ability_matches":
                        ability_matches,
                },
            }

            classifications.append(entry)
            counts[category] += 1

        output = {
            "source": str(CROSSWALK_PATH),
            "database": str(DB_PATH),
            "summary": {
                "unmatched_records":
                    len(classifications),
                "classification_counts":
                    dict(
                        sorted(
                            counts.items()
                        )
                    ),
            },
            "records": classifications,
        }

        OUTPUT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with OUTPUT_PATH.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                output,
                handle,
                indent=2,
                ensure_ascii=False,
            )

        print("=" * 60)
        print(" CLASSIFICATION SUMMARY")
        print("=" * 60)
        print()

        print(
            f"Unmatched records: "
            f"{len(classifications)}"
        )

        for category, count in sorted(
            counts.items()
        ):
            print(
                f"{category:28} {count}"
            )

        print()
        print("=" * 60)
        print(" NAME-VARIANT CHECK")
        print("=" * 60)

        name_variants = [
            item
            for item in classifications
            if item["category"]
            == "name_variant"
        ]

        for item in name_variants:
            print()
            print(
                f"{item['skill_name']}"
            )
            print(
                f"  URL: {item['url']}"
            )

            matches = item[
                "database_evidence"
            ][
                "stripped_skill_matches"
            ]

            if matches:
                for match in matches:
                    print(
                        f"  MATCH AFTER NORMALIZATION: "
                        f"skill_id="
                        f"{match['skill_id']} "
                        f"| "
                        f"{match['name']} "
                        f"| "
                        f"skill_line="
                        f"{match['skill_line']}"
                    )
            else:
                print(
                    "  No stripped-name skill match."
                )

        print()
        print("=" * 60)
        print(" CLASSIFICATION COMPLETE")
        print("=" * 60)
        print()
        print(
            f"Saved: {OUTPUT_PATH}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
