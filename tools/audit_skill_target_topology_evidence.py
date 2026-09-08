from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / "data" / "eso.db"

_CAPACITY_KEY_TOKENS = (
    "targetcount",
    "target_count",
    "maxtarget",
    "max_target",
    "maximumtarget",
    "maximum_target",
    "numtarget",
    "num_target",
)


def _capacity_fields(value: Any, *, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            normalized = str(key).casefold().replace("-", "_")
            compact = normalized.replace("_", "")
            if any(token in normalized or token.replace("_", "") in compact for token in _CAPACITY_KEY_TOKENS):
                yield child_path, child
            yield from _capacity_fields(child, path=child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield from _capacity_fields(child, path=child_path)


def audit(database: Path) -> str:
    geometry_counts: Counter[tuple[str, str]] = Counter()
    geometry_examples: dict[tuple[str, str], list[str]] = defaultdict(list)
    raw_capacity_counts: Counter[tuple[str, str]] = Counter()
    raw_capacity_examples: dict[tuple[str, str], list[str]] = defaultdict(list)
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
                skill_rank.radius AS radius,
                skill_rank.angle_distance AS angle_distance,
                skill_rank.raw_json AS raw_json
            FROM skill
            JOIN skill_rank ON skill_rank.skill_id = skill.id
            ORDER BY skill.name COLLATE NOCASE, skill_rank.rank, skill_rank.morph
            """
        )

        for row in rows:
            row_count += 1
            skill_name = str(row["skill_name"] or "<unnamed>")

            for field_name in ("radius", "angle_distance"):
                raw_value = row[field_name]
                try:
                    value = float(raw_value or 0.0)
                except (TypeError, ValueError):
                    continue
                if value <= 0.0:
                    continue
                key = (field_name, format(value, ".12g"))
                geometry_counts[key] += 1
                if skill_name not in geometry_examples[key] and len(geometry_examples[key]) < 8:
                    geometry_examples[key].append(skill_name)

            raw_text = row["raw_json"]
            if not raw_text:
                continue
            try:
                payload = json.loads(raw_text)
            except (TypeError, json.JSONDecodeError):
                malformed_raw_json += 1
                continue

            for field_path, field_value in _capacity_fields(payload):
                normalized_value = json.dumps(
                    field_value,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
                key = (field_path, normalized_value)
                raw_capacity_counts[key] += 1
                if skill_name not in raw_capacity_examples[key] and len(raw_capacity_examples[key]) < 5:
                    raw_capacity_examples[key].append(skill_name)

    lines = [
        "========================================",
        " SKILL TARGET TOPOLOGY EVIDENCE AUDIT",
        "========================================",
        f"Database: {database}",
        f"Skill-rank rows inspected: {row_count}",
        f"Malformed raw_json rows: {malformed_raw_json}",
        "",
        "Normalized geometry evidence",
        "----------------------------------------",
    ]

    if not geometry_counts:
        lines.append("No positive radius or angle_distance values found.")
    else:
        for key in sorted(geometry_counts, key=lambda item: (item[0], float(item[1]))):
            field_name, value = key
            examples = ", ".join(geometry_examples[key]) or "none"
            lines.append(
                f"{field_name}={value}: rows={geometry_counts[key]}; examples={examples}"
            )

    lines.extend(
        [
            "",
            "Target-capacity-like fields retained in skill_rank.raw_json",
            "----------------------------------------",
        ]
    )

    if not raw_capacity_counts:
        lines.append("No target-count/max-target-like raw_json fields found.")
    else:
        for field_path, value in sorted(
            raw_capacity_counts,
            key=lambda item: (item[0].casefold(), item[1].casefold()),
        ):
            examples = ", ".join(raw_capacity_examples[(field_path, value)]) or "none"
            lines.append(
                f"{field_path}={value}: rows={raw_capacity_counts[(field_path, value)]}; "
                f"examples={examples}"
            )

    lines.extend(
        [
            "",
            "Boundary",
            "----------------------------------------",
            "This audit reports source-backed geometry and retained raw capacity-like fields only.",
            "It does not infer target capacity from Area/Cone labels, radius, angle, or tooltip text.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect canonical skill geometry and target-capacity evidence without inference."
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
