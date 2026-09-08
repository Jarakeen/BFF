from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "eso.db"


def _target_fields(value: Any, *, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if "target" in str(key).casefold():
                yield child_path, child
            yield from _target_fields(child, path=child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield from _target_fields(child, path=child_path)


def audit(database: Path) -> str:
    target_counts: Counter[str] = Counter()
    target_examples: dict[str, list[str]] = defaultdict(list)
    raw_field_counts: Counter[tuple[str, str]] = Counter()
    raw_field_examples: dict[tuple[str, str], list[str]] = defaultdict(list)
    malformed_raw_json = 0
    row_count = 0

    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            """
            SELECT
                skill.name AS skill_name,
                skill.target AS skill_target,
                skill_rank.rank AS skill_rank,
                skill_rank.morph AS morph,
                skill_rank.raw_json AS raw_json
            FROM skill
            JOIN skill_rank ON skill_rank.skill_id = skill.id
            ORDER BY skill.name COLLATE NOCASE, skill_rank.rank, skill_rank.morph
            """
        )

        for row in rows:
            row_count += 1
            skill_name = str(row["skill_name"] or "<unnamed>")
            target_key = "NULL" if row["skill_target"] is None else str(row["skill_target"])
            target_counts[target_key] += 1
            if skill_name not in target_examples[target_key] and len(target_examples[target_key]) < 8:
                target_examples[target_key].append(skill_name)

            raw_text = row["raw_json"]
            if not raw_text:
                continue
            try:
                payload = json.loads(raw_text)
            except (TypeError, json.JSONDecodeError):
                malformed_raw_json += 1
                continue

            for field_path, field_value in _target_fields(payload):
                normalized_value = json.dumps(
                    field_value,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                key = (field_path, normalized_value)
                raw_field_counts[key] += 1
                if skill_name not in raw_field_examples[key] and len(raw_field_examples[key]) < 5:
                    raw_field_examples[key].append(skill_name)

    lines = [
        "========================================",
        " SKILL TARGET EVIDENCE AUDIT",
        "========================================",
        f"Database: {database}",
        f"Skill-rank rows inspected: {row_count}",
        f"Malformed raw_json rows: {malformed_raw_json}",
        "",
        "Opaque skill.target values",
        "----------------------------------------",
    ]

    for target_key in sorted(target_counts, key=lambda item: (item == "NULL", item)):
        examples = ", ".join(target_examples[target_key]) or "none"
        lines.append(
            f"target={target_key}: rows={target_counts[target_key]}; examples={examples}"
        )

    lines.extend(
        [
            "",
            "Target-related fields retained in skill_rank.raw_json",
            "----------------------------------------",
        ]
    )

    if not raw_field_counts:
        lines.append("No target-related raw_json fields found.")
    else:
        for field_path, value in sorted(
            raw_field_counts,
            key=lambda item: (item[0].casefold(), item[1].casefold()),
        ):
            examples = ", ".join(raw_field_examples[(field_path, value)]) or "none"
            lines.append(
                f"{field_path}={value}: rows={raw_field_counts[(field_path, value)]}; "
                f"examples={examples}"
            )

    lines.extend(
        [
            "",
            "Boundary",
            "----------------------------------------",
            "This audit reports evidence only. It does not map opaque integer target values",
            "to rotation target kinds and does not treat tooltip-text inference as canonical.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect canonical skill target evidence without inferring enum semantics."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Path to the ESO SQLite database.",
    )
    args = parser.parse_args()
    print(audit(args.database))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
