from __future__ import annotations

"""Read-only Phase 7 audit for temporal/runtime boundary rows.

This audit does not promote new mechanics or mutate canonical data. It starts
from the Phase 6 closeout gate, keeps only PHASE7_BOUNDARY rows, joins any
already-canonical component trigger relationship, and classifies the remaining
runtime concern at a deliberately coarse level.

The classifications describe *runtime work*, not effect identity. Phase 6
trigger relationships and EffectVariant remain authoritative for what an effect
is and what event can make it eligible.
"""

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.skill_component_trigger_relationship import SkillComponentTriggerType
from minmax.skill_component_trigger_relationship_repository import (
    SkillComponentTriggerRelationshipRepository,
)
from tools.audit_phase6_closeout import Phase6CloseoutRow, load_phase6_closeout

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class Phase7RuntimeBoundaryRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    trigger_types: tuple[SkillComponentTriggerType, ...]
    runtime_concerns: tuple[str, ...]
    reason: str
    signals: tuple[str, ...]
    fragment: str


_CADENCE_RE = re.compile(
    r"\bevery\s+\d+(?:\.\d+)?\s+seconds?\b|"
    r"\b\d+\s+times?\s+over\s+\d+(?:\.\d+)?\s+seconds?\b|"
    r"\bwith\s+each\b|\beach\s+time\b",
    re.IGNORECASE,
)
_DURATION_RE = re.compile(
    r"\bfor\s+\d+(?:\.\d+)?\s+seconds?\b|"
    r"\blasts?\s+(?:the\s+full\s+duration|\d+(?:\.\d+)?\s+seconds?)\b|"
    r"\bover\s+\d+(?:\.\d+)?\s+seconds?\b",
    re.IGNORECASE,
)
_DELAY_RE = re.compile(r"\bafter\s+\d+(?:\.\d+)?\s+seconds?\b", re.IGNORECASE)
_STATE_WINDOW_RE = re.compile(
    r"\bwhile\b|\buntil\b|\byour\s+next\b|\bnext\s+[^.;]{0,60}?\b(?:cast|use|attack)\b",
    re.IGNORECASE,
)
_CHANCE_RE = re.compile(r"\b\d+(?:\.\d+)?%\s+chance\b", re.IGNORECASE)
_COOLDOWN_RE = re.compile(
    r"\b(?:up\s+to|only)\s+once\s+every\s+\d+(?:\.\d+)?\s+seconds?\b|"
    r"\bcooldown\b",
    re.IGNORECASE,
)
_STACK_RE = re.compile(r"\b(?:stacks?|charges?)\b", re.IGNORECASE)
_STACK_THRESHOLD_RE = re.compile(
    r"\b(?:after\s+reaching|when\s+you\s+reach|upon\s+reaching)\s+\d+\s+(?:stacks?|charges?)\b",
    re.IGNORECASE,
)
_EVENT_GATE_RE = re.compile(
    r"\bactivating\s+again\b|"
    r"\bwhen\s+you\s+deal\s+damage\b|"
    r"\bcasting\s+(?:a|an)\s+[^.;]{0,80}?ability\b|"
    r"\bafter\s+reaching\s+\d+\s+(?:stacks?|charges?)\b",
    re.IGNORECASE,
)

_LIFECYCLE_TRIGGERS = frozenset(
    {
        SkillComponentTriggerType.EFFECT_ENDED,
        SkillComponentTriggerType.STUN_ENDED,
        SkillComponentTriggerType.STUN_FULL_DURATION,
        SkillComponentTriggerType.DAMAGE_OVER_TIME_EFFECT_ENDED,
    }
)
_ATTACK_TRIGGERS = frozenset(
    {
        SkillComponentTriggerType.LIGHT_ATTACK,
        SkillComponentTriggerType.HEAVY_ATTACK,
        SkillComponentTriggerType.LIGHT_OR_HEAVY_ATTACK,
    }
)
_TARGET_EVENT_TRIGGERS = frozenset(
    {
        SkillComponentTriggerType.TARGET_TAKES_DAMAGE,
        SkillComponentTriggerType.ENEMY_DIES_AFTER_STRIKE,
    }
)
_THRESHOLD_TRIGGERS = frozenset(
    {
        SkillComponentTriggerType.CHARGE_THRESHOLD_REACHED,
        SkillComponentTriggerType.STACK_THRESHOLD_REACHED,
    }
)


def classify_runtime_concerns(
    row: Phase6CloseoutRow,
    trigger_types: tuple[SkillComponentTriggerType, ...] = (),
) -> tuple[str, ...]:
    """Classify runtime responsibilities without inferring a new mechanic.

    ``trigger_resolution`` is intentionally not a trigger identity. It marks
    wording that clearly requires an event gate even though Phase 6 has not
    supplied a canonical SkillComponentTriggerRelationship for that row.
    """

    text = " ".join(str(row.fragment or "").split())
    concerns: list[str] = []

    def add(value: str) -> None:
        if value not in concerns:
            concerns.append(value)

    if trigger_types:
        add("trigger_detection")
    elif _EVENT_GATE_RE.search(text):
        add("trigger_resolution")

    if any(trigger in _ATTACK_TRIGGERS for trigger in trigger_types):
        add("attack_event")
    if any(trigger in _LIFECYCLE_TRIGGERS for trigger in trigger_types):
        add("effect_lifecycle")
    if any(trigger in _TARGET_EVENT_TRIGGERS for trigger in trigger_types):
        add("target_event")
    if any(trigger in _THRESHOLD_TRIGGERS for trigger in trigger_types):
        add("trigger_count")

    if _STACK_RE.search(text):
        add("stack_state")
    if _STACK_THRESHOLD_RE.search(text):
        add("stack_threshold")
    if _CHANCE_RE.search(text):
        add("chance")
    if _COOLDOWN_RE.search(text):
        add("cooldown")
    if SkillComponentTriggerType.DELAY_ELAPSED in trigger_types or _DELAY_RE.search(text):
        add("delay")
    if _CADENCE_RE.search(text):
        add("cadence")
    if _DURATION_RE.search(text):
        add("duration_window")
    if _STATE_WINDOW_RE.search(text):
        add("state_window")

    if not concerns:
        # The row is already proven to belong to Phase 7 by the Phase 6 closeout
        # audit. Preserve that fact while refusing to invent a narrower runtime
        # interpretation from wording we have not explicitly classified.
        add("runtime_review")

    return tuple(concerns)


def load_phase7_runtime_boundaries(
    database_path: str | Path,
) -> tuple[Phase7RuntimeBoundaryRow, ...]:
    database = Path(database_path)
    trigger_repository = SkillComponentTriggerRelationshipRepository(database)
    rows: list[Phase7RuntimeBoundaryRow] = []

    for row in load_phase6_closeout(database):
        if row.closeout_status != "PHASE7_BOUNDARY":
            continue

        relationships = trigger_repository.resolve(
            row.skill_rank_id,
            row.coefficient_number,
        )
        trigger_types = tuple(relationship.trigger_type for relationship in relationships)
        rows.append(
            Phase7RuntimeBoundaryRow(
                skill_rank_id=row.skill_rank_id,
                coefficient_number=row.coefficient_number,
                ability_id=row.ability_id,
                ability_name=row.ability_name,
                trigger_types=trigger_types,
                runtime_concerns=classify_runtime_concerns(row, trigger_types),
                reason=row.reason,
                signals=row.signals,
                fragment=row.fragment,
            )
        )

    return tuple(rows)


def summarize(rows: tuple[Phase7RuntimeBoundaryRow, ...]) -> dict[str, object]:
    concerns = Counter(concern for row in rows for concern in row.runtime_concerns)
    triggers = Counter(trigger.value for row in rows for trigger in row.trigger_types)
    return {
        "rows": len(rows),
        "concerns": concerns,
        "triggers": triggers,
        "without_canonical_trigger": sum(not row.trigger_types for row in rows),
        "trigger_resolution": sum("trigger_resolution" in row.runtime_concerns for row in rows),
        "runtime_review": sum("runtime_review" in row.runtime_concerns for row in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory Phase 7 runtime boundary rows without promoting new mechanics."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--samples", type=int, default=120)
    args = parser.parse_args()

    rows = load_phase7_runtime_boundaries(args.database)
    summary = summarize(rows)
    concerns: Counter[str] = summary["concerns"]  # type: ignore[assignment]
    triggers: Counter[str] = summary["triggers"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 7 RUNTIME BOUNDARY AUDIT")
    print("========================================")
    print(f"Database:                   {args.database}")
    print(f"Phase 7 boundary rows:      {summary['rows']}")
    print(f"Without canonical trigger: {summary['without_canonical_trigger']}")
    print(f"Need trigger resolution:   {summary['trigger_resolution']}")
    print(f"Runtime-review rows:        {summary['runtime_review']}")

    print("\nRUNTIME CONCERNS")
    for name, count in concerns.most_common():
        print(f"  {name:28} {count}")

    print("\nCANONICAL TRIGGER TYPES")
    if triggers:
        for name, count in triggers.most_common():
            print(f"  {name:28} {count}")
    else:
        print("  -")

    print(
        "\nNOTE: classifications describe runtime responsibilities only. "
        "They do not replace Phase 6 trigger relationships or EffectVariant identity/evidence."
    )

    ordered = sorted(
        rows,
        key=lambda row: (
            "runtime_review" not in row.runtime_concerns,
            "trigger_resolution" not in row.runtime_concerns,
            row.runtime_concerns,
            row.skill_rank_id,
            row.coefficient_number,
        ),
    )
    for row in ordered[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.ability_name}"
        )
        print(
            "trigger_types="
            + (",".join(trigger.value for trigger in row.trigger_types) if row.trigger_types else "-")
        )
        print(f"runtime_concerns={','.join(row.runtime_concerns)}")
        print(f"reason={row.reason}")
        if row.signals:
            print(f"signals={','.join(row.signals)}")
        if row.fragment:
            print(f"fragment={row.fragment}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
