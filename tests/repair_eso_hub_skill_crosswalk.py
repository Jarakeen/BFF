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
    / "eso_hub_skill_crosswalk_repaired.json"
)


def normalize(value):
    if not isinstance(value, str):
        return ""

    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def strip_skill_suffix(name):
    if not isinstance(name, str):
        return ""

    return re.sub(
        r"\s+skill$",
        "",
        name.strip(),
        flags=re.IGNORECASE,
    ).strip()


def classify_unmatched(record):
    name = record.get("skill_name", "")
    url = record.get("eso_hub_url", "")

    url_lower = url.casefold()

    if (
        "vengeance-" in url_lower
        or "vengeance/" in url_lower
    ):
        return "unresolved_special_variant"

    if "class-mastery" in url_lower:
        return "class_mastery"

    if "/dawns-wrath/" in url_lower:
        return "skill_line_dawns_wrath"

    if "/winters-embrace/" in url_lower:
        return "skill_line_winters_embrace"

    if normalize(name).endswith(" skill"):
        return "name_variant"

    return "other_unresolved"


def find_skill_matches(db, name):
    rows = db.execute(
        """
        SELECT
            id,
            name,
            skill_line,
            base_ability_id
        FROM skill
        WHERE lower(trim(name)) = lower(trim(?))
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


def find_ability_matches(db, name):
    rows = db.execute(
        """
        SELECT
            ability_id,
            name,
            skill_line,
            base_ability_id
        FROM ability
        WHERE lower(trim(name)) = lower(trim(?))
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


def unique_skill_match(matches):
    if len(matches) == 1:
        return matches[0]

    return None


def unique_ability_match(matches):
    if len(matches) == 1:
        return matches[0]

    return None


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" ESO-Hub Skill Crosswalk Repair")
    print("=" * 60)
    print()
    print("READ-ONLY DATABASE OPERATION")
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

    unmatched = crosswalk.get("unmatched", [])

    if not isinstance(unmatched, list):
        raise ValueError(
            "Crosswalk 'unmatched' must be a list."
        )

    db = sqlite3.connect(DB_PATH)

    repaired = []
    remaining = []
    counts = Counter()

    try:
        for item in unmatched:
            record = item.get("record", {})
            category = classify_unmatched(record)

            name = record.get(
                "skill_name",
                "",
            )

            candidate_names = [name]

            if category == "name_variant":
                stripped = strip_skill_suffix(name)

                if stripped and stripped != name:
                    candidate_names.append(stripped)

            skill_match = None
            ability_match = None
            matched_name = None

            # First try the exact source name, then the
            # normalized "Skill" suffix variant.
            for candidate in candidate_names:
                matches = find_skill_matches(
                    db,
                    candidate,
                )

                unique = unique_skill_match(matches)

                if unique is not None:
                    skill_match = unique
                    matched_name = candidate
                    break

            # If no unique skill exists, use a unique
            # ability match as evidence only.
            if skill_match is None:
                for candidate in candidate_names:
                    matches = find_ability_matches(
                        db,
                        candidate,
                    )

                    unique = unique_ability_match(matches)

                    if unique is not None:
                        ability_match = unique
                        matched_name = candidate
                        break

            result = {
                "index": item.get("index"),
                "skill_name": name,
                "url": record.get("eso_hub_url"),
                "classification": category,
                "matched_name": matched_name,
                "skill_match": skill_match,
                "ability_match": ability_match,
            }

            # Vengeance is deliberately never auto-repaired.
            if category == "unresolved_special_variant":
                result["resolution"] = "unresolved"
                result["reason"] = (
                    "ESO-Hub Vengeance variant. "
                    "Requires separate canonical-family "
                    "decision."
                )
                remaining.append(result)
                counts["vengeance_unresolved"] += 1
                continue

            if skill_match is not None:
                result["resolution"] = "skill_match"
                result["reason"] = (
                    "Unique existing skill identity found."
                )
                repaired.append(result)
                counts[
                    f"{category}_skill_match"
                ] += 1
                continue

            if ability_match is not None:
                result["resolution"] = "ability_match"
                result["reason"] = (
                    "Unique existing ability identity "
                    "found; skill identity requires "
                    "canonical crosswalk handling."
                )
                repaired.append(result)
                counts[
                    f"{category}_ability_match"
                ] += 1
                continue

            result["resolution"] = "unresolved"
            result["reason"] = (
                "No unique existing skill or ability "
                "identity found."
            )
            remaining.append(result)
            counts[
                f"{category}_unresolved"
            ] += 1

        output = {
            "source": str(CROSSWALK_PATH),
            "database": str(DB_PATH),
            "summary": {
                "original_unmatched": len(unmatched),
                "repaired": len(repaired),
                "remaining_unresolved": len(remaining),
                "counts": dict(
                    sorted(counts.items())
                ),
            },
            "repaired": repaired,
            "remaining_unresolved": remaining,
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
        print(" REPAIR SUMMARY")
        print("=" * 60)
        print()
        print(
            f"Original unmatched:     {len(unmatched)}"
        )
        print(
            f"Repaired candidates:    {len(repaired)}"
        )
        print(
            f"Still unresolved:       {len(remaining)}"
        )
        print()

        for key, value in sorted(counts.items()):
            print(
                f"{key:38} {value}"
            )

        print()
        print("=" * 60)
        print(" CROSSWALK REPAIR COMPLETE")
        print("=" * 60)
        print()
        print(
            f"Saved: {OUTPUT_PATH}"
        )
        print()
        print(
            "No database rows were changed."
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
