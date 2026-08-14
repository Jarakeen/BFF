import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "eso.db"
SOURCE_PATH = ROOT / "data" / "processed" / "noncrafted_potions_normalized.json"
REPORT_PATH = ROOT / "data" / "processed" / "noncrafted_potion_effect_import_v3_report.json"

BUFF_TO_EFFECT = {
    "Major Fortitude": "Fortitude",
    "Minor Fortitude": "Fortitude",
    "Major Intellect": "Intellect",
    "Minor Intellect": "Intellect",
    "Major Endurance": "Endurance",
    "Minor Endurance": "Endurance",
    "Major Brutality": "Brutality",
    "Minor Brutality": "Brutality",
    "Major Savagery": "Savagery",
    "Minor Savagery": "Savagery",
    "Major Prophecy": "Prophecy",
    "Minor Prophecy": "Prophecy",
    "Major Sorcery": "Sorcery",
    "Minor Sorcery": "Sorcery",
    "Major Expedition": "Expedition",
    "Minor Expedition": "Expedition",
    "Major Heroism": "Heroism",
    "Minor Heroism": "Heroism",
    "Major Protection": "Protection",
    "Minor Protection": "Protection",
    "Major Resolve": "Resolve",
    "Minor Resolve": "Resolve",
    "Major Evasion": "Evasion",
    "Minor Evasion": "Evasion",
    "Major Mending": "Mending",
    "Minor Mending": "Mending",
    "Major Vitality": "Vitality",
    "Minor Vitality": "Vitality",
    "Major Force": "Force",
    "Minor Force": "Force",
}


def load_source():
    with SOURCE_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    potions = data.get("potions")
    if not isinstance(potions, list):
        raise ValueError("Normalized source does not contain 'potions'.")
    return potions


def resolve_raw_effect_name(entity_type, name):
    if entity_type == "buff":
        return BUFF_TO_EFFECT.get(name, name)
    return name


def get_effect(db, name):
    rows = db.execute(
        "SELECT id, name, category FROM effect "
        "WHERE lower(name)=lower(?)",
        (name,),
    ).fetchall()
    if len(rows) == 1:
        return rows[0]
    if not rows:
        return None
    raise RuntimeError(
        f"Ambiguous effect {name!r}: "
        + ", ".join(str(r[0]) for r in rows)
    )


def find_potion_variants_from_sources(db, effect_id):
    """
    Do not infer variant type.

    Existing Potions sources are the authoritative bridge from
    effect -> effect_variant for this layer.
    """
    rows = db.execute(
        """
        SELECT DISTINCT
            ev.id,
            ev.effect_id,
            ev.type,
            ev.description,
            ev.icon,
            ev.raw_json
        FROM effect_source es
        JOIN effect_variant ev
          ON ev.id = es.effect_variant_id
        WHERE ev.effect_id = ?
          AND es.source_type = 'Potions'
        ORDER BY ev.id
        """,
        (effect_id,),
    ).fetchall()
    return rows


def find_matching_existing_source(
    db,
    variant_id,
    effect_name,
    potion_name,
):
    names = [
        f"{effect_name} {effect_name} {potion_name}",
        f"{effect_name} {potion_name}",
    ]

    for source_name in names:
        row = db.execute(
            """
            SELECT id
            FROM effect_source
            WHERE effect_variant_id = ?
              AND source_type = 'Potions'
              AND lower(source_name) = lower(?)
            """,
            (variant_id, source_name),
        ).fetchone()
        if row:
            return row[0], source_name

    return None, None


def main():
    print("=" * 60)
    print(" Black Feather Foundry")
    print(" Non-Crafted Potion Effect Relationship Importer v4")
    print("=" * 60)
    print()
    print("DATABASE OPERATION:")
    print("  effect_source ONLY")
    print()
    print("READ ONLY:")
    print("  entity")
    print("  effect")
    print("  effect_variant")
    print()
    print("TRANSACTIONAL: YES")
    print("NO NEW EFFECTS")
    print("NO NEW VARIANTS")
    print("NO ENTITY CHANGES")
    print()

    potions = load_source()
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")

    try:
        db.execute("BEGIN")

        effects_resolved = 0
        variants_resolved = 0
        sources_inserted = 0
        sources_existing = 0
        source_matches = 0
        errors = []

        for potion in potions:
            potion_name = potion["name"]

            for item in potion.get("effects", []):
                entity_id = item.get("entity_id")
                entity_type = item.get("entity_type")
                canonical_name = item.get("name")

                if not entity_id or not entity_type:
                    errors.append(
                        f"{potion_name}: malformed normalized effect"
                    )
                    continue

                entity = db.execute(
                    "SELECT entity_type, name FROM entity WHERE id=?",
                    (entity_id,),
                ).fetchone()

                if entity is None:
                    errors.append(
                        f"{potion_name}: canonical entity missing: "
                        f"{entity_id}"
                    )
                    continue

                actual_type, actual_name = entity

                if actual_type != entity_type:
                    errors.append(
                        f"{potion_name}: type mismatch for {entity_id}: "
                        f"{actual_type} != {entity_type}"
                    )
                    continue

                canonical_name = actual_name or canonical_name
                raw_effect_name = resolve_raw_effect_name(
                    entity_type,
                    canonical_name,
                )

                effect = get_effect(
                    db,
                    raw_effect_name,
                )

                if effect is None:
                    errors.append(
                        f"{potion_name}: effect not found: "
                        f"{canonical_name} -> {raw_effect_name}"
                    )
                    continue

                effect_id, effect_name, category = effect
                effects_resolved += 1

                variants = find_potion_variants_from_sources(
                    db,
                    effect_id,
                )

                if len(variants) == 0:
                    errors.append(
                        f"{potion_name}: no existing Potions "
                        f"effect_source/variant for {effect_name!r}"
                    )
                    continue

                if len(variants) > 1:
                    # The canonical buff name preserves Major/Minor rank,
                    # while raw effect names do not. Use that canonical rank
                    # to select the existing effect_variant. Do not use
                    # source_name as the variant selector because existing
                    # Potions sources may describe reagent traits/poisons
                    # rather than the normalized potion name.
                    desired_variant_type = None
                    if canonical_name.startswith("Major "):
                        desired_variant_type = "Major"
                    elif canonical_name.startswith("Minor "):
                        desired_variant_type = "Minor"

                    if desired_variant_type:
                        ranked = [
                            variant
                            for variant in variants
                            if (variant[2] or "").casefold()
                            == desired_variant_type.casefold()
                        ]

                        if len(ranked) == 1:
                            variant = ranked[0]
                        elif len(ranked) == 0:
                            errors.append(
                                f"{potion_name}: no existing Potions "
                                f"variant with type {desired_variant_type!r} "
                                f"for {effect_name!r}"
                            )
                            continue
                        else:
                            errors.append(
                                f"{potion_name}: multiple existing Potions "
                                f"variants with type {desired_variant_type!r} "
                                f"for {effect_name!r}"
                            )
                            continue
                    else:
                        # No Major/Minor rank is available in the canonical
                        # entity name, so do not guess among multiple variants.
                        errors.append(
                            f"{potion_name}: multiple existing Potions "
                            f"variants for {effect_name!r}; canonical "
                            f"buff name {canonical_name!r} has no rank"
                        )
                        continue
                else:
                    variant = variants[0]

                variant_id = variant[0]
                variants_resolved += 1

                existing_id, existing_name = (
                    find_matching_existing_source(
                        db,
                        variant_id,
                        effect_name,
                        potion_name,
                    )
                )

                if existing_id:
                    sources_existing += 1
                    continue

                raw_text = (
                    item.get("raw_match")
                    or potion.get(
                        "ability_description_raw",
                        "",
                    )
                )

                source_name = (
                    f"{effect_name} "
                    f"{effect_name} "
                    f"{potion_name}"
                )

                db.execute(
                    """
                    INSERT INTO effect_source (
                        effect_variant_id,
                        source_type,
                        source_name,
                        condition,
                        raw_text
                    )
                    VALUES (?, 'Potions', ?, ?, ?)
                    """,
                    (
                        variant_id,
                        source_name,
                        item.get("condition"),
                        raw_text,
                    ),
                )

                sources_inserted += 1

        if errors:
            db.rollback()

            report = {
                "status": "aborted",
                "database_changes_committed": False,
                "potions_processed": len(potions),
                "effects_resolved": effects_resolved,
                "variants_resolved": variants_resolved,
                "sources_inserted": sources_inserted,
                "sources_existing": sources_existing,
                "source_matches": source_matches,
                "errors": errors,
            }

            with REPORT_PATH.open("w", encoding="utf-8") as f:
                json.dump(
                    report,
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            print("=" * 60)
            print(" IMPORT ABORTED")
            print("=" * 60)
            print()
            print(f"Effects resolved:      {effects_resolved}")
            print(f"Variants resolved:     {variants_resolved}")
            print(f"Sources inserted:      {sources_inserted}")
            print(f"Sources existing:      {sources_existing}")
            print(f"Errors:                {len(errors)}")
            print()
            print("No database changes were committed.")
            print()
            for error in errors[:100]:
                print(f"  {error}")

            raise RuntimeError(
                "Non-crafted potion effect import v4 failed."
            )

        db.commit()

        report = {
            "status": "complete",
            "database_changes_committed": True,
            "potions_processed": len(potions),
            "effects_resolved": effects_resolved,
            "variants_resolved": variants_resolved,
            "sources_inserted": sources_inserted,
            "sources_existing": sources_existing,
            "source_matches": source_matches,
            "errors": [],
        }

        with REPORT_PATH.open("w", encoding="utf-8") as f:
            json.dump(
                report,
                f,
                indent=2,
                ensure_ascii=False,
            )

        print("=" * 60)
        print(" EFFECT IMPORT V3 COMPLETE")
        print("=" * 60)
        print()
        print(f"Potions processed:      {len(potions)}")
        print(f"Effects resolved:       {effects_resolved}")
        print(f"Variants resolved:      {variants_resolved}")
        print(f"Sources inserted:       {sources_inserted}")
        print(f"Sources already there:  {sources_existing}")
        print("Errors:                 0")
        print()
        print("Database changes committed.")
        print(f"Report: {REPORT_PATH}")

    except Exception:
        if db.in_transaction:
            db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
