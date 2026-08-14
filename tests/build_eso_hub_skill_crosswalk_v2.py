import json
import re
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "eso.db"
SOURCE_PATH = BASE_DIR / "data" / "raw" / "eso_hub_skill_data.json"


def normalize(value):
    if not isinstance(value, str):
        return ""

    value = value.casefold().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def parse_url(url):
    if not isinstance(url, str):
        return None

    marker = "/en/skills/"

    if marker not in url:
        return None

    path = url.split(marker, 1)[1]
    path = path.split("?", 1)[0]
    path = path.split("#", 1)[0]

    parts = [
        part.strip()
        for part in path.split("/")
        if part.strip()
    ]

    if len(parts) < 2:
        return None

    return {
        "parts": parts,
        "category": normalize(parts[0]),
        "skill_line": normalize(
            parts[-2]
        ),
        "name_slug": normalize(
            parts[-1]
        ),
    }


def get_weapon_line(record):
    weapon = record.get("weapon")

    if isinstance(weapon, dict):
        return normalize(
            weapon.get("skill_line")
        )

    if isinstance(weapon, list):
        for item in weapon:
            if isinstance(item, dict):
                value = normalize(
                    item.get("skill_line")
                )
                if value:
                    return value

    return ""


def classify_url(parsed):
    if not parsed:
        return "unknown"

    category = parsed["category"]

    if category == "weapon":
        return "weapon"

    if category in {
        "class",
        "nightblade",
        "sorcerer",
        "dragonknight",
        "templar",
        "warden",
        "necromancer",
        "arcanist",
    }:
        return "class"

    if category == "alliance war":
        return "alliance"

    if category in {
        "guild",
        "world",
        "racial",
        "ava",
    }:
        return "other"

    return category


def candidate_matches(
    record,
    candidate,
    parsed,
):
    reasons = []
    score = 0

    eso_name = normalize(
        record.get("skill_name")
    )

    db_name = normalize(
        candidate["name"]
    )

    if eso_name != db_name:
        return None

    score += 100
    reasons.append("exact name")

    eso_line = parsed["skill_line"] if parsed else ""
    db_line = normalize(
        candidate["skill_line"]
    )

    weapon_line = get_weapon_line(
        record
    )

    expected_line = (
        weapon_line
        or eso_line
    )

    if expected_line:

        if db_line == expected_line:

            score += 100
            reasons.append(
                "skill line match"
            )

        else:

            return None

    category = (
        classify_url(parsed)
        if parsed
        else "unknown"
    )

    # Weapon URL must resolve to a weapon
    # skill line.
    if category == "weapon":

        if not weapon_line:

            return None

        if db_line != weapon_line:

            return None

        score += 50
        reasons.append(
            "weapon category match"
        )

    return {
        "skill_id": candidate["id"],
        "name": candidate["name"],
        "skill_line": candidate["skill_line"],
        "base_ability_id":
            candidate["base_ability_id"],
        "score": score,
        "reasons": reasons,
    }


def find_skill_candidates(
    record,
    db,
):
    name = record.get("skill_name")
    parsed = parse_url(
        record.get("eso_hub_url")
    )

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

    matches = []

    for row in rows:

        candidate = {
            "id": row[0],
            "name": row[1],
            "skill_line": row[2],
            "base_ability_id": row[3],
        }

        match = candidate_matches(
            record,
            candidate,
            parsed,
        )

        if match:
            matches.append(match)

    return matches


def find_ability_candidates(
    record,
    db,
):
    name = record.get("skill_name")

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

    results = []

    parsed = parse_url(
        record.get("eso_hub_url")
    )

    weapon_line = get_weapon_line(
        record
    )

    expected_line = (
        weapon_line
        or (
            parsed["skill_line"]
            if parsed
            else ""
        )
    )

    for row in rows:

        ability_id = row[0]
        ability_name = row[1]
        skill_line = normalize(
            row[2]
        )
        base_ability_id = row[3]

        if expected_line:

            if skill_line != expected_line:
                continue

        results.append(
            {
                "ability_id": ability_id,
                "name": ability_name,
                "skill_line": row[2],
                "base_ability_id":
                    base_ability_id,
            }
        )

    return results


def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" ESO-Hub Skill Crosswalk v2")
    print("=" * 60)
    print()
    print("READ-ONLY")
    print()

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:

        data = json.load(handle)

    records = (
        data.get("skills", [])
        if isinstance(data, dict)
        else data
    )
    OUTPUT_PATH = BASE_DIR / "data" / "processed" / "eso_hub_skill_crosswalk_v2.json"
    if not isinstance(records, list):
        raise ValueError(
            "ESO-Hub source does not contain "
            "a skills list."
        )

    db = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    matched = []
    ambiguous = []
    unmatched = []
    non_skill = []

    try:

        for index, record in enumerate(
            records,
            start=1,
        ):

            if not isinstance(
                record,
                dict,
            ):
                continue

            skill_matches = (
                find_skill_candidates(
                    record,
                    db,
                )
            )

            if len(skill_matches) == 1:

                matched.append(
                    {
                        "index": index,
                        "record": record,
                        "match": skill_matches[0],
                    }
                )

                continue

            if len(skill_matches) > 1:

                ambiguous.append(
                    {
                        "index": index,
                        "record": record,
                        "matches": skill_matches,
                    }
                )

                continue

            ability_matches = (
                find_ability_candidates(
                    record,
                    db,
                )
            )

            if ability_matches:

                non_skill.append(
                    {
                        "index": index,
                        "record": record,
                        "abilities":
                            ability_matches,
                    }
                )

                continue

            unmatched.append(
                {
                    "index": index,
                    "record": record,
                }
            )

        print("=" * 60)
        print(" CROSSWALK SUMMARY")
        print("=" * 60)
        print()

        print(
            f"ESO-Hub records: {len(records)}"
        )
        print(
            f"Matched skills:  {len(matched)}"
        )
        print(
            f"Ambiguous:       {len(ambiguous)}"
        )
        print(
            f"Ability fallback: {len(non_skill)}"
        )
        print(
            f"Unmatched:       {len(unmatched)}"
        )

        print()

        # ----------------------------------------------------
        # Known tests
        # ----------------------------------------------------

        print("=" * 60)
        print(" KNOWN TESTS")
        print("=" * 60)

        known = {
            "Wall of Elements",
            "Pierce Armor",
            "Executioner",
            "Aggressive Horn",
        }

        for name in known:

            print()
            print(name)

            for item in matched:

                if (
                    normalize(
                        item["record"].get(
                            "skill_name"
                        )
                    )
                    != normalize(name)
                ):
                    continue

                match = item["match"]

                print(
                    "  MATCHED"
                )

                print(
                    f"    URL: "
                    f"{item['record'].get('eso_hub_url')}"
                )

                print(
                    f"    skill_id: "
                    f"{match['skill_id']}"
                )

                print(
                    f"    skill_line: "
                    f"{match['skill_line']}"
                )

                print(
                    f"    base_ability_id: "
                    f"{match['base_ability_id']}"
                )

                print(
                    f"    reasons: "
                    f"{', '.join(match['reasons'])}"
                )

            for item in non_skill:

                if (
                    normalize(
                        item["record"].get(
                            "skill_name"
                        )
                    )
                    != normalize(name)
                ):
                    continue

                print(
                    "  ABILITY FALLBACK"
                )

                print(
                    f"    URL: "
                    f"{item['record'].get('eso_hub_url')}"
                )

                for ability in item[
                    "abilities"
                ]:

                    print(
                        f"    ability_id: "
                        f"{ability['ability_id']} "
                        f"| "
                        f"skill_line: "
                        f"{ability['skill_line']}"
                    )

            for item in ambiguous:

                if (
                    normalize(
                        item["record"].get(
                            "skill_name"
                        )
                    )
                    != normalize(name)
                ):
                    continue

                print(
                    "  AMBIGUOUS"
                )

                print(
                    f"    URL: "
                    f"{item['record'].get('eso_hub_url')}"
                )

                for match in item[
                    "matches"
                ]:

                    print(
                        f"    skill_id: "
                        f"{match['skill_id']} "
                        f"| "
                        f"skill_line: "
                        f"{match['skill_line']}"
                    )

            found = (
                any(
                    normalize(
                        item["record"].get(
                            "skill_name"
                        )
                    )
                    == normalize(name)
                    for item in matched
                )
                or any(
                    normalize(
                        item["record"].get(
                            "skill_name"
                        )
                    )
                    == normalize(name)
                    for item in non_skill
                )
                or any(
                    normalize(
                        item["record"].get(
                            "skill_name"
                        )
                    )
                    == normalize(name)
                    for item in ambiguous
                )
            )

            if not found:
                print(
                    "  UNMATCHED"
                )

        # ----------------------------------------------------
        # Unmatched list
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print(" UNMATCHED SKILLS")
        print("=" * 60)

        for item in unmatched:

            record = item["record"]

            print(
                f"[{item['index']}] "
                f"{record.get('skill_name')}"
            )

            print(
                f"  {record.get('eso_hub_url')}"
            )

        # ----------------------------------------------------
        # Ambiguous list
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print(" AMBIGUOUS SKILLS")
        print("=" * 60)

        for item in ambiguous:

            record = item["record"]

            print(
                f"[{item['index']}] "
                f"{record.get('skill_name')}"
            )

            print(
                f"  {record.get('eso_hub_url')}"
            )

            for match in item["matches"]:

                print(
                    f"    "
                    f"skill_id={match['skill_id']} "
                    f"| "
                    f"skill_line="
                    f"{match['skill_line']}"
                )
        # ----------------------------------------------------
        # Save crosswalk artifact
        # ----------------------------------------------------

        output = {
            "source": str(SOURCE_PATH),
            "database": str(DB_PATH),
            "summary": {
                "eso_hub_records": len(records),
                "matched_skills": len(matched),
                "ability_fallback": len(non_skill),
                "ambiguous": len(ambiguous),
                "unmatched": len(unmatched),
            },
            "matched": matched,
            "ability_fallback": non_skill,
            "ambiguous": ambiguous,
            "unmatched": unmatched,
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

        print()
        print(
            f"Crosswalk saved: {OUTPUT_PATH}"
        )

        print()
        print("=" * 60)
        print(" CROSSWALK V2 COMPLETE")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    main()
