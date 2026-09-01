from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_skill_component_import_gaps import ImportGapRow, load_import_gaps


DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class Phase6GapRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    name: str
    phase3_reasons: tuple[str, ...]
    disposition: str
    signals: tuple[str, ...]
    linked_effects: tuple[str, ...]
    named_combat_effects: tuple[str, ...]
    fragment: str


def _table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def _normalize(value: object) -> str:
    return " ".join(str(value or "").split())


def _contains_pattern(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def semantic_signals(text: str) -> tuple[str, ...]:
    """Return conservative Phase 6 audit cues, never mechanic conclusions.

    ``text`` must be the coefficient-owned fragment whenever one exists. The
    audit deliberately avoids borrowing unrelated clauses from the rest of an
    ability tooltip because a multi-component skill can mix damage, healing,
    resources, and conditions that belong to different coefficient slots.
    """

    signals: list[str] = []
    patterns = (
        ("execute_candidate", r"\bexecute\b|\b(?:below|under|less than)\s+\d+(?:\.\d+)?%?\s+health\b"),
        ("resource_event_candidate", r"\b(?:restore|restores|restoring|gain|gains)\b[^.;]{0,80}\b(?:magicka|stamina|ultimate)\b"),
        ("shield_candidate", r"\bdamage shield\b|\bshield\b[^.;]{0,60}\babsorbs?\b"),
        ("healing_candidate", r"\bheal(?:ing|s|ed)?\b|\brestore(?:s|d|ing)?\b[^.;]{0,60}\bhealth\b"),
        ("secondary_component_candidate", r"\b(?:also|additional(?:ly)?|then)\b[^.;]{0,100}\b(?:damage|heal|shield|restore)\b"),
        ("conditional_candidate", r"\b(?:if|while|when|whenever|after|upon)\b"),
        (
            "temporal_proc_candidate",
            r"\bchance\b|\bcooldown\b|\bonce every\b|\bstacks?\b|\bper stack\b",
        ),
    )
    for label, pattern in patterns:
        if _contains_pattern(text, pattern):
            signals.append(label)
    return tuple(signals)


def _disposition(gap: ImportGapRow, signals: tuple[str, ...], linked_effects: tuple[str, ...], named_effects: tuple[str, ...]) -> str:
    if "slot_mismatch" in gap.reasons or "missing_fragment" in gap.reasons:
        return "source_evidence"
    if named_effects or linked_effects or signals:
        if "temporal_proc_candidate" in signals:
            return "phase7_boundary_candidate"
        return "richer_component_semantics"
    if gap.reasons == ("effect_kind",):
        return "parser_coverage"
    return "classification_field_gap"


def _load_context(database_path: Path) -> tuple[dict[int, str], dict[int, tuple[str, ...]], tuple[str, ...]]:
    descriptions: dict[int, str] = {}
    linked_effects: dict[int, tuple[str, ...]] = {}
    combat_effect_names: tuple[str, ...] = ()

    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        if _table_exists(db, "ability"):
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)")}
            text_columns = [column for column in ("coef_description", "raw_description", "raw_tooltip") if column in columns]
            if text_columns:
                sql = "SELECT ability_id, " + ", ".join(text_columns) + " FROM ability"
                for row in db.execute(sql):
                    descriptions[int(row["ability_id"])] = " ".join(_normalize(row[column]) for column in text_columns)

        required = {"ability_effect_link", "effect_variant", "effect"}
        if all(_table_exists(db, name) for name in required):
            buckets: dict[int, set[str]] = {}
            for row in db.execute(
                """
                SELECT ael.ability_id, e.name
                FROM ability_effect_link ael
                JOIN effect_variant ev ON ev.id = ael.effect_variant_id
                JOIN effect e ON e.id = ev.effect_id
                WHERE e.name IS NOT NULL AND TRIM(e.name) <> ''
                """
            ):
                buckets.setdefault(int(row[0]), set()).add(str(row[1]).strip())
            linked_effects = {
                ability_id: tuple(sorted(names, key=str.casefold))
                for ability_id, names in buckets.items()
            }

        if _table_exists(db, "combat_effect"):
            combat_effect_names = tuple(
                str(row[0]).strip()
                for row in db.execute(
                    "SELECT name FROM combat_effect WHERE name IS NOT NULL AND TRIM(name) <> '' ORDER BY name"
                )
            )

    return descriptions, linked_effects, combat_effect_names


def _matched_named_effects(text: str, names: tuple[str, ...]) -> tuple[str, ...]:
    lower = text.casefold()
    return tuple(name for name in names if name.casefold() in lower)


def load_phase6_gap_matrix(database_path: str | Path, *, limit: int | None = None) -> tuple[Phase6GapRow, ...]:
    path = Path(database_path)
    gaps = load_import_gaps(path, limit=limit)
    descriptions, linked_by_ability, combat_effect_names = _load_context(path)

    rows: list[Phase6GapRow] = []
    for gap in gaps:
        ability_context = descriptions.get(gap.ability_id, "")
        component_text = _normalize(gap.fragment) or ability_context
        signals = semantic_signals(component_text)
        linked = linked_by_ability.get(gap.ability_id, ())
        named = _matched_named_effects(component_text, combat_effect_names)
        rows.append(
            Phase6GapRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                name=gap.name,
                phase3_reasons=gap.reasons,
                disposition=_disposition(gap, signals, linked, named),
                signals=signals,
                linked_effects=linked,
                named_combat_effects=named,
                fragment=gap.fragment,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[Phase6GapRow, ...]) -> dict[str, Counter[str] | int]:
    dispositions = Counter(row.disposition for row in rows)
    signals = Counter(signal for row in rows for signal in row.signals)
    linked = sum(bool(row.linked_effects) for row in rows)
    named = sum(bool(row.named_combat_effects) for row in rows)
    return {
        "rows": len(rows),
        "dispositions": dispositions,
        "signals": signals,
        "with_linked_effects": linked,
        "with_named_combat_effects": named,
    }


def _clean(value: object, *, max_len: int = 260) -> str:
    text = _normalize(value)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a read-only Phase 6 gap matrix over unresolved active skill components. "
            "Signals are audit candidates only and never populate canonical mechanics."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_phase6_gap_matrix(args.database, limit=args.limit)
    summary = summarize(rows)
    dispositions: Counter[str] = summary["dispositions"]  # type: ignore[assignment]
    signals: Counter[str] = summary["signals"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 COMPONENT GAP MATRIX")
    print("========================================")
    print(f"Database:                  {args.database}")
    print(f"Unresolved active rows:    {summary['rows']}")
    print(f"With linked EffectVariant: {summary['with_linked_effects']}")
    print(f"With named combat effect:  {summary['with_named_combat_effects']}")

    print("\nDISPOSITION")
    for name, count in dispositions.most_common():
        print(f"  {name:28} {count}")

    print("\nSEMANTIC CANDIDATE SIGNALS")
    for name, count in signals.most_common():
        print(f"  {name:28} {count}")

    print("\nNOTE: candidate signals are evidence triage, not canonical classifications.")
    print("No database rows are written and no mechanic is promoted by this audit.")

    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.name}"
        )
        print(f"phase3_gap={','.join(row.phase3_reasons)}")
        print(f"disposition={row.disposition}")
        if row.signals:
            print(f"signals={','.join(row.signals)}")
        if row.linked_effects:
            print(f"linked_effects={', '.join(row.linked_effects)}")
        if row.named_combat_effects:
            print(f"named_combat_effects={', '.join(row.named_combat_effects)}")
        if row.fragment:
            print(f"fragment={_clean(row.fragment)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
