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

from minmax.skill_component_condition_repository import SkillComponentConditionRepository
from minmax.skill_component_text_evidence import extract_component_text_evidence
from tools.audit_skill_coefficient_slots import load_slot_audit
from tools.audit_skill_component_text_semantics import is_active_coefficient

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class ConditionConsequenceAuditRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    threshold: float
    fragment: str
    cues: tuple[str, ...]


def consequence_cues(text: str) -> tuple[str, ...]:
    lower = " ".join(str(text or "").casefold().split())
    cues: list[str] = []
    if re.search(r"\bdamage\b", lower):
        cues.append("damage")
    if re.search(r"\bheal(?:s|ed|ing)?\b", lower) or re.search(r"\brestore(?:s|d|ing)?\s+health\b", lower):
        cues.append("healing")
    if re.search(r"\bshield\b|\babsorbs?\b", lower):
        cues.append("shield")
    if re.search(r"\b(?:magicka|stamina|ultimate)\b", lower) and re.search(r"\b(?:restore(?:s|d|ing)?|gain(?:s|ed|ing)?)\b", lower):
        cues.append("resource")
    return tuple(cues)


def load_condition_consequence_evidence(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[ConditionConsequenceAuditRow, ...]:
    path = Path(database_path)
    repository = SkillComponentConditionRepository(path)
    rows: list[ConditionConsequenceAuditRow] = []

    with sqlite3.connect(path) as db:
        descriptions = {
            int(row[0]): str(row[1] or "")
            for row in db.execute("SELECT ability_id, coef_description FROM ability")
        }

    for slot in load_slot_audit(path, limit=limit):
        if not is_active_coefficient(slot):
            continue
        conditions = repository.resolve(slot.skill_rank_id, slot.coefficient_number)
        if not conditions:
            continue
        evidence = extract_component_text_evidence(
            descriptions.get(slot.ability_id, ""),
            slot.coefficient_number,
        )
        for condition in conditions:
            rows.append(
                ConditionConsequenceAuditRow(
                    skill_rank_id=slot.skill_rank_id,
                    coefficient_number=slot.coefficient_number,
                    ability_id=slot.ability_id,
                    ability_name=slot.name,
                    threshold=condition.threshold,
                    fragment=evidence.fragment,
                    cues=consequence_cues(evidence.fragment),
                )
            )
    return tuple(rows)


def summarize(rows: tuple[ConditionConsequenceAuditRow, ...]) -> Counter[str]:
    return Counter(cue for row in rows for cue in row.cues)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit consequence evidence for Phase 6 conditioned components.")
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()

    rows = load_condition_consequence_evidence(args.database, limit=args.limit)
    print("\n========================================")
    print(" PHASE 6 CONDITION CONSEQUENCE EVIDENCE")
    print("========================================")
    print(f"Database:              {args.database}")
    print(f"Conditioned components:{len(rows):7}")
    print("\nCONSEQUENCE CUES")
    for cue, count in summarize(rows).most_common():
        print(f"  {cue:28} {count}")
    print("\nNOTE: cues are evidence triage only; no consequence is promoted canonically.")

    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(f"threshold={row.threshold * 100:.1f}%")
        print(f"cues={','.join(row.cues) if row.cues else 'none'}")
        print(f"fragment={' '.join(row.fragment.split())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
