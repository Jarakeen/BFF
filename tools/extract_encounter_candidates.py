from __future__ import annotations

"""Read-only candidate extraction for existing UESP boss JSON.

This tool does not modify JSON or eso.db. It inspects the already-collected
boss records and reports source-supported mechanic facts plus conservative
phase candidates for human review before anything is promoted into the
canonical encounter knowledge layer.
"""

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.uesp.mechanic_classifier import classify_mechanic


EXPLICIT_PHASE_RE = re.compile(r"(?i)\b(?:phase\s+(\d+|[ivx]+)|final\s+phase)\b")
PERCENT_RE = re.compile(r"(?i)\b(\d{1,3})\s*%\s*(?:health)?\b")
AT_PERCENT_RE = re.compile(
    r"(?i)\b(?:at|below|under|when(?:\s+\w+){0,4}\s+reaches?|upon reaching)\s+"
    r"(\d{1,3})\s*%\s*(?:health)?\b"
)
SLASH_PERCENT_RE = re.compile(r"(?i)\b(\d{1,3})\s*%\s*/\s*(\d{1,3})\s*%\s*(?:health)?\b")
TRANSITION_RE = re.compile(
    r"(?i)\b(?:"
    r"becomes?\s+(?:untargetable|invulnerable|immune)|"
    r"disappears?|vanishes?|teleports?|transitions?|"
    r"enters?\s+(?:a|the|its)?\s*(?:new|next|final)?\s*phase|"
    r"begins?\s+(?:a|the)?\s*(?:new|next|final)?\s*phase|"
    r"starts?\s+(?:a|the)?\s*(?:new|next|final)?\s*phase|"
    r"returns?\s+to\s+the\s+fight|reappears?"
    r")\b"
)
INTERMISSION_RE = re.compile(
    r"(?i)\b(?:intermission|portal\s+phase|add\s+phase|execute\s+phase|final\s+phase)\b"
)

RESPONSE_CUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("block", re.compile(r"(?i)\bblock(?:ed|ing)?\b|\bcan be blocked\b")),
    ("knockback", re.compile(r"(?i)\bknock(?:s|ed|ing)?\s*back\b|\bknockback\b")),
    ("stun", re.compile(r"(?i)\bstun(?:s|ned|ning)?\b")),
    ("safe_zone", re.compile(r"(?i)\bsafe (?:area|zone)\b|\bgives? protection\b|\bprotection from\b")),
    ("adds", re.compile(r"(?i)\badds?\b|\bspawn(?:s|ed|ing)?\b|\bsummons?\b")),
)


@dataclass(frozen=True)
class EvidenceBlock:
    section: str
    name: str
    text: str


@dataclass(frozen=True)
class PhaseCandidate:
    label: str
    threshold: str
    confidence: str
    reason: str
    section: str
    source_name: str
    evidence: str


@dataclass(frozen=True)
class MechanicCandidate:
    name: str
    section: str
    confidence: str
    mechanic_type: str | None
    damage_type: str | None
    target_count: int | None
    requires_movement: bool | None
    requires_positioning: bool | None
    requires_cleanse: bool | None
    persistent_hazard: bool | None
    failure_is_fatal: bool | None
    interruptible: bool | None
    interrupt_note: str
    response_cues: tuple[str, ...]
    evidence: str


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _iter_named_rows(payload: Any) -> Iterable[tuple[str, str]]:
    if not isinstance(payload, list):
        return
    for index, row in enumerate(payload, start=1):
        if isinstance(row, dict):
            name = _clean(row.get("name") or row.get("label") or f"row {index}")
            description = _clean(
                row.get("description")
                or row.get("strategy")
                or row.get("note")
                or row.get("text")
            )
            if description:
                yield name, description
        elif isinstance(row, str) and row.strip():
            yield f"row {index}", _clean(row)


def evidence_blocks(record: dict[str, Any]) -> list[EvidenceBlock]:
    blocks: list[EvidenceBlock] = []

    for name, text in _iter_named_rows(record.get("abilities")):
        blocks.append(EvidenceBlock("ability", name, text))

    for name, text in _iter_named_rows(record.get("mechanics")):
        blocks.append(EvidenceBlock("structured_mechanic", name, text))

    for key in ("strategy_notes", "notes"):
        for name, text in _iter_named_rows(record.get(key)):
            blocks.append(EvidenceBlock(key, name, text))

    difficulty = record.get("difficulty_notes")
    if isinstance(difficulty, dict):
        for key, rows in difficulty.items():
            for name, text in _iter_named_rows(rows):
                blocks.append(EvidenceBlock(f"difficulty:{key}", name, text))

    dialogue = record.get("dialogue")
    if isinstance(dialogue, list):
        for index, row in enumerate(dialogue, start=1):
            if not isinstance(row, dict):
                continue
            trigger = _clean(row.get("trigger"))
            if trigger:
                speaker = _clean(row.get("speaker")) or "dialogue"
                blocks.append(EvidenceBlock("dialogue_trigger", f"{speaker} {index}", trigger))

    return blocks


def _phase_label(match: re.Match[str]) -> str:
    text = match.group(0)
    token = match.group(1)
    if token:
        return f"Phase {token.upper()}"
    if "final" in text.casefold():
        return "Final Phase"
    return text.strip()


def extract_phase_candidates(blocks: Iterable[EvidenceBlock]) -> list[PhaseCandidate]:
    results: list[PhaseCandidate] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add(candidate: PhaseCandidate) -> None:
        key = (
            candidate.label.casefold(),
            candidate.threshold,
            candidate.section,
            candidate.source_name.casefold(),
        )
        if key not in seen:
            seen.add(key)
            results.append(candidate)

    for block in blocks:
        text = block.text
        explicit_matches = list(EXPLICIT_PHASE_RE.finditer(text))
        if explicit_matches:
            percentages = PERCENT_RE.findall(text)
            threshold = f"{percentages[0]}%" if len(percentages) == 1 else ""
            for match in explicit_matches:
                add(
                    PhaseCandidate(
                        label=_phase_label(match),
                        threshold=threshold,
                        confidence="high",
                        reason="explicit phase language in source text",
                        section=block.section,
                        source_name=block.name,
                        evidence=text,
                    )
                )

        slash_match = SLASH_PERCENT_RE.search(text)
        if slash_match and TRANSITION_RE.search(text):
            for value in slash_match.groups():
                add(
                    PhaseCandidate(
                        label=f"Threshold transition at {value}%",
                        threshold=f"{value}%",
                        confidence="medium",
                        reason="health threshold paired with an explicit transition cue",
                        section=block.section,
                        source_name=block.name,
                        evidence=text,
                    )
                )
            continue

        threshold_match = AT_PERCENT_RE.search(text)
        if threshold_match and TRANSITION_RE.search(text):
            value = threshold_match.group(1)
            add(
                PhaseCandidate(
                    label=f"Threshold transition at {value}%",
                    threshold=f"{value}%",
                    confidence="medium",
                    reason="health threshold paired with an explicit transition cue",
                    section=block.section,
                    source_name=block.name,
                    evidence=text,
                )
            )

        if INTERMISSION_RE.search(text) and not explicit_matches:
            add(
                PhaseCandidate(
                    label="Named intermission/phase",
                    threshold="",
                    confidence="medium",
                    reason="source explicitly names an intermission or specialized phase",
                    section=block.section,
                    source_name=block.name,
                    evidence=text,
                )
            )

    return results


def _response_cues(text: str) -> tuple[str, ...]:
    return tuple(label for label, pattern in RESPONSE_CUE_PATTERNS if pattern.search(text))


def extract_mechanic_candidates(record: dict[str, Any]) -> list[MechanicCandidate]:
    results: list[MechanicCandidate] = []
    abilities = record.get("abilities")
    if not isinstance(abilities, list):
        return results

    for index, row in enumerate(abilities, start=1):
        if not isinstance(row, dict):
            continue
        name = _clean(row.get("name")) or f"Ability {index}"
        description = _clean(row.get("description"))
        if not description:
            continue

        classification = classify_mechanic(name, description)
        response_cues = _response_cues(description)

        behavioral_facts = [
            classification.mechanic_type,
            classification.target_count,
            classification.requires_movement,
            classification.requires_positioning,
            classification.requires_cleanse,
            classification.persistent_hazard,
            classification.failure_is_fatal,
            classification.interruptible,
        ]
        has_behavioral_fact = any(
            value is not None and value is not False for value in behavioral_facts
        )

        # Damage type is useful metadata once an ability is a mechanic, but a
        # basic attack does not become a mechanic merely because it deals frost,
        # physical, or other typed damage.
        if not has_behavioral_fact and not response_cues:
            continue

        explicit_action = any(
            value is True
            for value in (
                classification.requires_cleanse,
                classification.failure_is_fatal,
                classification.interruptible,
            )
        ) or any(cue in response_cues for cue in ("block", "safe_zone"))
        confidence = "high" if explicit_action else "medium"

        mechanic_type = classification.mechanic_type
        if "safe_zone" in response_cues and mechanic_type == "summon":
            # Preserve the summon cue in response_cues, but prefer the actual
            # player-facing environmental behavior for review.
            mechanic_type = "environment"

        results.append(
            MechanicCandidate(
                name=name,
                section="ability",
                confidence=confidence,
                mechanic_type=mechanic_type,
                damage_type=classification.damage_type,
                target_count=classification.target_count,
                requires_movement=classification.requires_movement,
                requires_positioning=classification.requires_positioning,
                requires_cleanse=classification.requires_cleanse,
                persistent_hazard=classification.persistent_hazard,
                failure_is_fatal=classification.failure_is_fatal,
                interruptible=classification.interruptible,
                interrupt_note=classification.interrupt_note,
                response_cues=response_cues,
                evidence=description,
            )
        )

    return results


def load_records(directory: Path, boss_filter: str = "") -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    needle = boss_filter.casefold().strip()
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if needle:
            haystack = " ".join(
                [path.stem, _clean(payload.get("id")), _clean(payload.get("name"))]
            ).casefold()
            if needle not in haystack:
                continue
        records.append((path, payload))
    return records


def _clip(text: str, width: int = 180) -> str:
    text = _clean(text)
    return text if len(text) <= width else text[: width - 3].rstrip() + "..."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only extraction of phase and mechanic candidates from existing UESP boss JSON"
    )
    parser.add_argument("--boss-dir", default="data/uesp/bosses")
    parser.add_argument("--boss", default="", help="Filter by boss id/name substring")
    parser.add_argument("--limit", type=int, default=25, help="Maximum detailed bosses to print; 0 means all")
    parser.add_argument("--json-output", default="", help="Optional report path; never writes to eso.db or source JSON")
    args = parser.parse_args()

    boss_dir = Path(args.boss_dir)
    records = load_records(boss_dir, args.boss)

    report: list[dict[str, Any]] = []
    bosses_with_phases = 0
    bosses_with_mechanics = 0
    phase_count = 0
    mechanic_count = 0
    high_phase_count = 0
    medium_phase_count = 0

    for path, record in records:
        phases = extract_phase_candidates(evidence_blocks(record))
        mechanics = extract_mechanic_candidates(record)
        if phases:
            bosses_with_phases += 1
        if mechanics:
            bosses_with_mechanics += 1
        phase_count += len(phases)
        mechanic_count += len(mechanics)
        high_phase_count += sum(item.confidence == "high" for item in phases)
        medium_phase_count += sum(item.confidence == "medium" for item in phases)
        report.append(
            {
                "id": _clean(record.get("id")) or path.stem,
                "name": _clean(record.get("name")) or path.stem,
                "content_id": _clean(record.get("content_id")),
                "source_url": _clean((record.get("source") or {}).get("url")) if isinstance(record.get("source"), dict) else "",
                "phase_candidates": [asdict(item) for item in phases],
                "mechanic_candidates": [asdict(item) for item in mechanics],
            }
        )

    print("=" * 68)
    print(" ENCOUNTER CANDIDATE EXTRACTION - READ ONLY")
    print("=" * 68)
    print(f"boss directory:              {boss_dir}")
    print(f"boss records examined:       {len(records)}")
    print(f"bosses with phase candidates:{bosses_with_phases:8}")
    print(f"phase candidates:            {phase_count:8}")
    print(f"  high confidence:           {high_phase_count:8}")
    print(f"  medium confidence:         {medium_phase_count:8}")
    print(f"bosses with mechanic facts:  {bosses_with_mechanics:8}")
    print(f"mechanic candidates:         {mechanic_count:8}")
    print()

    if args.boss and not records:
        print(f"No raw boss JSON matched filter: {args.boss!r}")
        print("This usually means the boss was not collected into data/uesp/bosses.")
        print()

    interesting = [row for row in report if row["phase_candidates"] or row["mechanic_candidates"]]
    detail_rows = interesting if args.limit == 0 else interesting[: max(args.limit, 0)]

    for row in detail_rows:
        print(f"--- {row['name']} [{row['id']}] ---")
        if row["phase_candidates"]:
            print("  PHASE CANDIDATES")
            for item in row["phase_candidates"]:
                threshold = f" | threshold={item['threshold']}" if item["threshold"] else ""
                print(f"    [{item['confidence'].upper()}] {item['label']}{threshold}")
                print(f"      source={item['section']}:{item['source_name']}")
                print(f"      reason={item['reason']}")
                print(f"      evidence={_clip(item['evidence'])}")
        if row["mechanic_candidates"]:
            print("  MECHANIC CANDIDATES")
            for item in row["mechanic_candidates"]:
                facts = []
                for key in (
                    "mechanic_type",
                    "damage_type",
                    "target_count",
                    "requires_movement",
                    "requires_positioning",
                    "requires_cleanse",
                    "persistent_hazard",
                    "failure_is_fatal",
                    "interruptible",
                ):
                    value = item[key]
                    if value is not None and value is not False:
                        facts.append(f"{key}={value}")
                if item["response_cues"]:
                    facts.append("response_cues=" + ",".join(item["response_cues"]))
                print(f"    [{item['confidence'].upper()}] {item['name']}: {', '.join(facts)}")
                print(f"      evidence={_clip(item['evidence'])}")
        print()

    if len(interesting) > len(detail_rows):
        print(f"Detailed output limited to {len(detail_rows)} of {len(interesting)} bosses with candidates.")
        print("Use --limit 0 for all, or --boss <name> for one encounter.")
        print()

    if args.json_output:
        output = Path(args.json_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"JSON report written: {output}")
        print()

    print("No database rows or source JSON files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
