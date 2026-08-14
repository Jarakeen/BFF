import json
import re
import sqlite3
from pathlib import Path


# ============================================================
# Paths
# ============================================================

BASE_DIR = (
    Path(__file__).resolve().parent.parent
)

DB_PATH = (
    BASE_DIR
    / "data"
    / "eso.db"
)

SOURCE_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "eso_hub_skill_data.json"
)


# ============================================================
# Helpers
# ============================================================


def normalize(value):
    if not isinstance(value, str):
        return ""

    value = value.casefold().strip()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def normalize_skill_line(value):
    value = normalize(value)

    aliases = {
        "two handed": "two handed",
        "two hand": "two handed",
        "one hand and shield":
            "one hand and shield",
        "destruction staff":
            "destruction staff",
        "restoration staff":
            "restoration staff",
        "dual wield":
            "dual wield",
        "bow":
            "bow",
    }

    return aliases.get(
        value,
        value,
    )


def parse_eso_hub_skill_url(url):
    """
    Convert:

        https://eso-hub.com/en/skills/
        weapon/destruction-staff/wall-of-elements

    into:

        {
            "category": "weapon",
            "skill_line": "destruction staff",
            "slug": "wall of elements"
        }
    """

    if not isinstance(
        url,
        str,
    ):
        return None

    marker = "/en/skills/"

    if marker not in url:
        return None

    path = url.split(
        marker,
        1,
    )[1]

    path = path.split(
        "?",
        1,
    )[0]

    path = path.split(
        "#",
        1,
    )[0]

    parts = [
        part.strip()
        for part in path.split("/")
        if part.strip()
    ]

    if len(parts) < 2:
        return None

    return {
        "category": parts[0],
        "skill_line": (
            parts[1]
            .replace("-", " ")
        ),
        "slug": (
            parts[-1]
            .replace("-", " ")
        ),
        "parts": parts,
    }


# ============================================================
# Candidate Matching
# ============================================================


def find_candidates(
    skill,
    db,
):
    name = skill.get(
        "skill_name"
    )

    url = skill.get(
        "eso_hub_url"
    )

    normalized_name = normalize(
        name
    )

    parsed = parse_eso_hub_skill_url(
        url
    )

    if not normalized_name:
        return []

    # --------------------------------------------------------
    # First: exact skill-name candidates
    # --------------------------------------------------------

    candidates = db.execute(
        """
        SELECT
            id,
            name,
            skill_line,
            class_type,
            skill_type,
            base_ability_id
        FROM skill
        WHERE lower(name) = lower(?)
        ORDER BY id
        """,
        (name,),
    ).fetchall()

    # --------------------------------------------------------
    # Score candidates
    # --------------------------------------------------------

    scored = []

    for row in candidates:

        (
            skill_id,
            db_name,
            db_skill_line,
            class_type,
            skill_type,
            base_ability_id,
        ) = row

        score = 0
        reasons = []

        # Exact normalized name
        if normalize(db_name) == normalized_name:

            score += 100

            reasons.append(
                "exact name"
            )

        # ----------------------------------------------------
        # Skill-line comparison
        # ----------------------------------------------------

        eso_skill_line = ""

        if parsed:
            eso_skill_line = (
                parsed["skill_line"]
            )

        if eso_skill_line:

            if (
                normalize_skill_line(
                    db_skill_line
                )
                ==
                normalize_skill_line(
                    eso_skill_line
                )
            ):

                score += 50

                reasons.append(
                    "skill line match"
                )

        # ----------------------------------------------------
        # Weapon metadata comparison
        # ----------------------------------------------------

        weapon = skill.get(
            "weapon"
        )

        if isinstance(
            weapon,
            dict,
        ):

            weapon_line = weapon.get(
                "skill_line"
            )

            if weapon_line:

                if (
                    normalize_skill_line(
                        db_skill_line
                    )
                    ==
                    normalize_skill_line(
                        weapon_line
                    )
                ):

                    score += 75

                    reasons.append(
                        "weapon skill line match"
                    )

        elif isinstance(
            weapon,
            list,
        ):

            for weapon_item in weapon:

                if not isinstance(
                    weapon_item,
                    dict,
                ):
                    continue

                weapon_line = weapon_item.get(
                    "skill_line"
                )

                if not weapon_line:
                    continue

                if (
                    normalize_skill_line(
                        db_skill_line
                    )
                    ==
                    normalize_skill_line(
                        weapon_line
                    )
                ):

                    score += 75

                    reasons.append(
                        "weapon skill line match"
                    )

                    break

        # ----------------------------------------------------
        # Base ability name confirmation
        # ----------------------------------------------------

        if base_ability_id:

            ability = db.execute(
                """
                SELECT name
                FROM ability
                WHERE ability_id = ?
                """,
                (base_ability_id,),
            ).fetchone()

            if ability:

                if (
                    normalize(
                        ability[0]
                    )
                    ==
                    normalized_name
                ):

                    score += 25

                    reasons.append(
                        "base ability name match"
                    )

        scored.append(
            {
                "skill_id": skill_id,
                "name": db_name,
                "skill_line": db_skill_line,
                "class_type": class_type,
                "skill_type": skill_type,
                "base_ability_id":
                    base_ability_id,
                "score": score,
                "reasons": reasons,
            }
        )

    scored.sort(
        key=lambda item: (
            -item["score"],
            item["skill_id"],
        )
    )

    return scored


# ============================================================
# Main
# ============================================================


def main():

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" ESO-Hub Skill Crosswalk")
    print("=" * 60)
    print()

    print(
        "READ-ONLY MODE"
    )

    print(
        "No database changes will be made."
    )

    print()

    # --------------------------------------------------------
    # Load ESO-Hub data
    # --------------------------------------------------------

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:

        data = json.load(
            handle
        )

    if isinstance(
        data,
        dict,
    ):

        records = data.get(
            "skills",
            [],
        )

    else:

        records = data

    if not isinstance(
        records,
        list,
    ):

        raise ValueError(
            "ESO-Hub data does not contain "
            "a skills list."
        )

    # --------------------------------------------------------
    # Open DB read-only
    # --------------------------------------------------------

    db = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:

        matched = []
        ambiguous = []
        unmatched = []

        # ----------------------------------------------------
        # Match every ESO-Hub skill
        # ----------------------------------------------------

        for index, skill in enumerate(
            records,
            start=1,
        ):

            if not isinstance(
                skill,
                dict,
            ):
                continue

            name = skill.get(
                "skill_name"
            )

            url = skill.get(
                "eso_hub_url"
            )

            candidates = find_candidates(
                skill,
                db,
            )

            if not candidates:

                unmatched.append(
                    {
                        "index": index,
                        "name": name,
                        "url": url,
                    }
                )

                continue

            best_score = (
                candidates[0]["score"]
            )

            best = [
                candidate
                for candidate in candidates
                if candidate["score"]
                == best_score
            ]

            if (
                best_score >= 100
                and len(best) == 1
            ):

                matched.append(
                    {
                        "index": index,
                        "name": name,
                        "url": url,
                        "candidate": best[0],
                    }
                )

            else:

                ambiguous.append(
                    {
                        "index": index,
                        "name": name,
                        "url": url,
                        "candidates":
                            candidates,
                    }
                )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print(" CROSSWALK SUMMARY")
        print("=" * 60)
        print()

        print(
            f"ESO-Hub records: {len(records)}"
        )

        print(
            f"Matched:         {len(matched)}"
        )

        print(
            f"Ambiguous:       {len(ambiguous)}"
        )

        print(
            f"Unmatched:       {len(unmatched)}"
        )

        print()

        # ----------------------------------------------------
        # Ambiguous
        # ----------------------------------------------------

        if ambiguous:

            print("=" * 60)
            print(" AMBIGUOUS MATCHES")
            print("=" * 60)

            for item in ambiguous:

                print()
                print(
                    f"[{item['index']}] "
                    f"{item['name']}"
                )

                print(
                    f"URL: {item['url']}"
                )

                for candidate in item[
                    "candidates"
                ]:

                    print(
                        "  "
                        f"skill_id="
                        f"{candidate['skill_id']} "
                        f"| "
                        f"skill_line="
                        f"{candidate['skill_line']} "
                        f"| "
                        f"score="
                        f"{candidate['score']}"
                    )

                    if candidate[
                        "reasons"
                    ]:

                        print(
                            "      "
                            + ", ".join(
                                candidate[
                                    "reasons"
                                ]
                            )
                        )

        # ----------------------------------------------------
        # Unmatched
        # ----------------------------------------------------

        if unmatched:

            print()
            print("=" * 60)
            print(" UNMATCHED SKILLS")
            print("=" * 60)

            for item in unmatched:

                print()
                print(
                    f"[{item['index']}] "
                    f"{item['name']}"
                )

                print(
                    f"URL: {item['url']}"
                )

        # ----------------------------------------------------
        # Known tests
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print(" KNOWN SKILL TESTS")
        print("=" * 60)

        for test_name in (
            "Wall of Elements",
            "Pierce Armor",
            "Executioner",
            "Aggressive Horn",
        ):

            results = [
                item
                for item in matched
                if normalize(
                    item["name"]
                )
                == normalize(
                    test_name
                )
            ]

            ambiguous_results = [
                item
                for item in ambiguous
                if normalize(
                    item["name"]
                )
                == normalize(
                    test_name
                )
            ]

            if results:

                for item in results:

                    candidate = item[
                        "candidate"
                    ]

                    print()
                    print(
                        f"PASS: "
                        f"{item['name']}"
                    )

                    print(
                        f"  ESO-Hub: "
                        f"{item['url']}"
                    )

                    print(
                        f"  Internal skill: "
                        f"{candidate['skill_id']}"
                    )

                    print(
                        f"  Skill line: "
                        f"{candidate['skill_line']}"
                    )

                    print(
                        f"  Base ability: "
                        f"{candidate['base_ability_id']}"
                    )

            elif ambiguous_results:

                print()
                print(
                    f"AMBIGUOUS: "
                    f"{test_name}"
                )

            else:

                print()
                print(
                    f"UNMATCHED: "
                    f"{test_name}"
                )

        print()
        print("=" * 60)
        print(" CROSSWALK COMPLETE")
        print("=" * 60)

    finally:

        db.close()


if __name__ == "__main__":
    main()