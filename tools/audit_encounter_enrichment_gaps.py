from __future__ import annotations

"""Read-only audit of encounter enrichment gaps in existing UESP boss JSON.

This deliberately does not write to eso.db or source JSON. It measures:
- explicit and implicit threshold-transition evidence missed by the first pass
- actionable mechanic language in ability descriptions
- boss records with thin/no ability data
- trial/dungeon/arena content records with empty boss_ids

The goal is to decide what can be recovered locally before any targeted recrawl.
"""

import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable


PERCENT_TOKEN_RE = re.compile(r"(?i)\b(\d{1,3})\s*%")
TRANSITION_CUE_RE = re.compile(
    r"(?i)\b(?:"
    r"disappears?|vanishes?|teleports?|"
    r"becomes?\s+(?:untargetable|invulnerable|immune)|"
    r"returns?\s+to\s+the\s+fight|reappears?|"
    r"transforms?|changes?\s+form|"
    r"enters?\s+(?:a|the|its)?\s*(?:new|next|final)?\s*phase|"
    r"begins?\s+(?:a|the)?\s*(?:new|next|final)?\s*phase|"
    r"starts?\s+(?:a|the)?\s*(?:new|next|final)?\s*phase"
    r")\b"
)
EXPLICIT_PHASE_RE = re.compile(r"(?i)\b(?:phase\s+(?:\d+|[ivx]+)|final\s+phase|intermission)\b")
ACTIONABLE_RE = re.compile(
    r"(?i)\b(?:"
    r"block(?:ed|ing)?|dodge(?:d|roll)?|interrupt(?:ed|ible|ing)?|"
    r"cleanse(?:d|s)?|purge(?:d|s)?|spread|stack|"
    r"knock(?:s|ed|ing)?\s*back|knockdown|knocks?\s+down|stun(?:s|ned|ning)?|"
    r"snare(?:s|d)?|fear(?:s|ed)?|"
    r"safe\s+(?:area|zone|circle|spot)|"
    r"move\s+(?:out|away|through)|run\s+(?:out|away|through)|avoid|"
    r"portal|summons?|spawns?|adds?|"
    r"invulnerable|untargetable|immune|"
    r"one[- ]shot|fatal|kills?\s+(?:a|the|all)?\s*players?"
    r")\b"
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def ability_rows(record: dict[str, Any]) -> Iterable[tuple[str, str]]:
    rows = record.get("abilities")
    if not isinstance(rows, list):
        return
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        name = clean(row.get("name")) or f"Ability {index}"
        description = clean(row.get("description"))
        if description:
            yield name, description


def threshold_transition_evidence(record: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for ability_name, text in ability_rows(record):
        percentages = [int(v) for v in PERCENT_TOKEN_RE.findall(text)]
        if not percentages:
            continue
        transition = bool(TRANSITION_CUE_RE.search(text))
        explicit_phase = bool(EXPLICIT_PHASE_RE.search(text))
        if not transition and not explicit_phase:
            continue
        results.append(
            {
                "ability": ability_name,
                "thresholds": percentages,
                "explicit_phase": explicit_phase,
                "transition_cue": transition,
                "evidence": text,
            }
        )
    return results


def actionable_abilities(record: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for ability_name, text in ability_rows(record):
        matches = sorted({m.group(0).casefold() for m in ACTIONABLE_RE.finditer(text)})
        if matches:
            results.append(
                {
                    "ability": ability_name,
                    "cues": ", ".join(matches),
                    "evidence": text,
                }
            )
    return results


def clip(text: str, width: int = 180) -> str:
    text = clean(text)
    return text if len(text) <= width else text[: width - 3].rstrip() + "..."


def content_inventory(root: Path) -> tuple[int, list[tuple[str, str, str]]]:
    total = 0
    empty: list[tuple[str, str, str]] = []
    for folder in ("trials", "dungeons", "arenas"):
        directory = root / folder
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            record = load_json(path)
            if not record:
                continue
            total += 1
            boss_ids = record.get("boss_ids")
            if not isinstance(boss_ids, list) or not boss_ids:
                empty.append((folder[:-1], clean(record.get("name")) or path.stem, path.name))
    return total, empty


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit recoverable encounter-enrichment gaps without changing data")
    parser.add_argument("--uesp-root", default="data/uesp")
    parser.add_argument("--limit", type=int, default=30, help="Detailed rows to print per section; 0 means all")
    args = parser.parse_args()

    root = Path(args.uesp_root)
    boss_dir = root / "bosses"
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(boss_dir.glob("*.json")):
        record = load_json(path)
        if record:
            records.append((path, record))

    threshold_bosses: list[dict[str, Any]] = []
    actionable_bosses = 0
    actionable_rows = 0
    bosses_without_abilities: list[tuple[str, str]] = []
    bosses_with_abilities_but_no_actionable: list[tuple[str, str, int]] = []

    for path, record in records:
        boss_id = clean(record.get("id")) or path.stem
        name = clean(record.get("name")) or path.stem
        abilities = list(ability_rows(record))
        if not abilities:
            bosses_without_abilities.append((name, boss_id))

        transitions = threshold_transition_evidence(record)
        if transitions:
            threshold_bosses.append({"name": name, "id": boss_id, "rows": transitions})

        actionable = actionable_abilities(record)
        if actionable:
            actionable_bosses += 1
            actionable_rows += len(actionable)
        elif abilities:
            bosses_with_abilities_but_no_actionable.append((name, boss_id, len(abilities)))

    content_total, empty_content = content_inventory(root)

    threshold_rows = sum(len(row["rows"]) for row in threshold_bosses)
    threshold_values = sum(len(item["thresholds"]) for row in threshold_bosses for item in row["rows"])

    print("=" * 72)
    print(" ENCOUNTER ENRICHMENT GAP AUDIT - READ ONLY")
    print("=" * 72)
    print(f"boss JSON records:                         {len(records):6}")
    print(f"bosses with threshold-transition evidence:{len(threshold_bosses):6}")
    print(f"threshold-transition ability rows:         {threshold_rows:6}")
    print(f"threshold values represented:              {threshold_values:6}")
    print(f"bosses with actionable ability language:   {actionable_bosses:6}")
    print(f"actionable ability rows:                    {actionable_rows:6}")
    print(f"bosses with no ability rows:                {len(bosses_without_abilities):6}")
    print(f"bosses with abilities but no action cues:   {len(bosses_with_abilities_but_no_actionable):6}")
    print(f"content JSON records examined:              {content_total:6}")
    print(f"content records with empty boss_ids:        {len(empty_content):6}")
    print()

    limit = None if args.limit == 0 else max(args.limit, 0)

    print("=== THRESHOLD / TRANSITION EVIDENCE ===")
    shown = threshold_bosses if limit is None else threshold_bosses[:limit]
    for boss in shown:
        print(f"  {boss['name']} [{boss['id']}]")
        for row in boss["rows"]:
            labels = ", ".join(f"{v}%" for v in row["thresholds"])
            kind = "explicit-phase" if row["explicit_phase"] else "transition"
            print(f"    {row['ability']}: {labels} | {kind}")
            print(f"      {clip(row['evidence'])}")
    if limit is not None and len(threshold_bosses) > len(shown):
        print(f"  ... {len(threshold_bosses) - len(shown)} more bosses")
    print()

    print("=== BOSS RECORDS WITH NO ABILITIES ===")
    shown_missing = bosses_without_abilities if limit is None else bosses_without_abilities[:limit]
    for name, boss_id in shown_missing:
        print(f"  {name} [{boss_id}]")
    if limit is not None and len(bosses_without_abilities) > len(shown_missing):
        print(f"  ... {len(bosses_without_abilities) - len(shown_missing)} more")
    print()

    print("=== CONTENT RECORDS WITH EMPTY boss_ids ===")
    shown_content = empty_content if limit is None else empty_content[:limit]
    for kind, name, filename in shown_content:
        print(f"  {kind:7} | {name} | {filename}")
    if limit is not None and len(empty_content) > len(shown_content):
        print(f"  ... {len(empty_content) - len(shown_content)} more")
    print()

    print("Interpretation:")
    print("  - threshold/transition rows are recovery candidates, not canonical phases")
    print("  - empty boss_ids means content-to-boss discovery is incomplete even when achievements/summary text names bosses")
    print("  - bosses with no abilities are the strongest targeted recrawl/recovery candidates")
    print()
    print("No database rows or source JSON files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
