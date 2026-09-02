from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_phase6_other_richer_semantics import detail_category
from tools.audit_phase6_richer_semantics_taxonomy import richer_category
from tools.audit_phase6_signal_only_semantics import signal_only_category
from tools.audit_phase6_remaining_semantics import load_remaining_phase6_semantics
from minmax.skill_component_text_evidence import extract_component_text_evidence

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


@dataclass(frozen=True)
class Phase6CloseoutRow:
    skill_rank_id: int
    coefficient_number: int
    ability_id: int
    ability_name: str
    disposition: str
    closeout_status: str
    reason: str
    signals: tuple[str, ...]
    fragment: str


_CLEAR_CLASSIFICATION_RICHER = {
    "direct_heal_classification_gap",
}

_CLEAR_OTHER = {
    "periodic_damage_classification_gap",
}


def _has_trigger_signal(signals: tuple[str, ...]) -> bool:
    return "conditional_candidate" in signals or "temporal_proc_candidate" in signals


def _is_phase7_cadence_only(fragment: str) -> bool:
    """Return True for explicit repeat/state cadence with no extra Phase 6 rule."""

    text = " ".join(str(fragment or "").split()).casefold()
    count_word = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)"
    patterns = (
        r"\bcalls\s+upon\b[^.;]{0,100}?\bevery\s+\d+(?:\.\d+)?\s+seconds?\b",
        r"\bwhile\s+the\s+field\s+grows\b[^.;]{0,140}?\bevery\s+\d+(?:\.\d+)?\s+seconds?\b",
        rf"\bsmashes?\b[^.;]{{0,80}}?\b{count_word}\s+times?\s+over\s+\d+(?:\.\d+)?\s+seconds?\b[^.;]{{0,120}}?\bwith\s+each\s+smash\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _neighbor_owns_interrupt_immunity(fragment: str, coefficient_number: int) -> bool:
    """Detect utility wording explicitly owned by a later shield component.

    Decimal timing values (for example ``0.3 seconds``) may occur between the
    damage component and the shield clause, so this matcher deliberately does
    not use periods as sentence boundaries. Ownership still requires a distinct
    later coefficient placeholder inside the explicit damage-shield clause.
    """

    text = " ".join(str(fragment or "").split()).casefold()
    current = rf"\${int(coefficient_number)}(?!\d)"
    match = re.search(
        rf"{current}.{{0,180}}?\b(?:magic|flame|frost|shock|physical|poison|disease|bleed)?\s*damage\b"
        rf".{{0,280}}?\bdamage\s+shield\b.{{0,160}}?\$(?P<shield_coef>\d+)(?!\d)"
        rf".{{0,140}}?\binterrupt\s+immunity\b",
        text,
        re.IGNORECASE,
    )
    return match is not None and int(match.group("shield_coef")) != int(coefficient_number)


def _closeout_status(item) -> tuple[str, str]:
    gap = item.gap

    if gap.disposition == "classification_field_gap":
        return "CLASSIFICATION_CLEANUP", "original classification-field gap; no new Phase 6 mechanic implied"

    if gap.disposition == "phase7_boundary_candidate":
        return "PHASE7_BOUNDARY", "original audit already identified timing/trigger/state semantics"

    if gap.disposition == "source_evidence":
        return "SOURCE_EVIDENCE_BLOCKED", "canonical source fragment is missing or insufficient"

    if gap.disposition == "parser_coverage":
        return "NEEDS_PHASE6_REVIEW", "parser coverage still prevents a trustworthy component interpretation"

    if gap.disposition != "richer_component_semantics":
        return "NEEDS_PHASE6_REVIEW", f"unrecognized remaining disposition: {gap.disposition}"

    if _is_phase7_cadence_only(gap.fragment):
        return "PHASE7_BOUNDARY", "component identity is known; remaining repeat/state cadence belongs to Phase 7"

    if _neighbor_owns_interrupt_immunity(gap.fragment, gap.coefficient_number):
        return "OWNERSHIP_NEGATIVE", "interrupt immunity belongs to the neighboring shield component"

    evidence = extract_component_text_evidence(gap.fragment, gap.coefficient_number)
    richer = richer_category(gap.fragment, gap.coefficient_number, evidence.effect_kind)

    if richer in _CLEAR_CLASSIFICATION_RICHER:
        if _has_trigger_signal(gap.signals):
            return (
                "NEEDS_PHASE6_REVIEW",
                f"{richer} with unresolved static trigger relationship",
            )
        return "CLASSIFICATION_CLEANUP", richer

    if richer == "multi_damage_classification_gap":
        if _has_trigger_signal(gap.signals):
            return "NEEDS_PHASE6_REVIEW", "multi-damage row also carries unresolved conditional/temporal semantics"
        return "CLASSIFICATION_CLEANUP", richer

    if richer in {
        "stored_damage_scaling",
        "per_tick_damage_ramp",
        "utility_relationship_candidate",
        "conditional_or_temporal_candidate",
    }:
        return "NEEDS_PHASE6_REVIEW", richer

    if richer != "other_richer_semantics":
        return "NEEDS_PHASE6_REVIEW", richer

    from tools.audit_phase6_richer_semantics_taxonomy import RicherSemanticsTaxonomyRow

    taxonomy_row = RicherSemanticsTaxonomyRow(
        skill_rank_id=gap.skill_rank_id,
        coefficient_number=gap.coefficient_number,
        ability_id=gap.ability_id,
        ability_name=gap.name,
        category=richer,
        effect_kind=evidence.effect_kind,
        signals=gap.signals,
        fragment=gap.fragment,
    )
    detail = detail_category(taxonomy_row)

    if detail == "signal_only_candidate":
        signal_category = signal_only_category(taxonomy_row.fragment, taxonomy_row.effect_kind)
        if signal_category == "multi_heal_classification_gap":
            return "CLASSIFICATION_CLEANUP", signal_category
        if signal_category == "phase7_attack_triggered_heal":
            return "NEEDS_PHASE6_REVIEW", "attack-triggered heal needs static Phase 6 trigger relationship"
        return "NEEDS_PHASE6_REVIEW", signal_category

    if detail == "damage_scaling_or_modifier_candidate":
        if "heals you for" in gap.fragment.casefold() and "scaling off your max health" in gap.fragment.casefold():
            return "OWNERSHIP_NEGATIVE", "neighboring heal owns the Max Health scaling wording"
        return "NEEDS_PHASE6_REVIEW", detail

    if detail in _CLEAR_OTHER:
        if _has_trigger_signal(gap.signals):
            return "NEEDS_PHASE6_REVIEW", f"{detail} with unresolved conditional/temporal signal"
        return "CLASSIFICATION_CLEANUP", detail

    if detail in {"direct_damage_classification_gap", "secondary_damage_classification_gap"}:
        if _has_trigger_signal(gap.signals):
            return "NEEDS_PHASE6_REVIEW", f"{detail} with unresolved conditional/temporal signal"
        return "CLASSIFICATION_CLEANUP", detail

    if detail == "damage_with_duration_or_cadence":
        return "NEEDS_PHASE6_REVIEW", "duration/cadence row may also carry a same-component static effect relationship"

    return "NEEDS_PHASE6_REVIEW", detail


def load_phase6_closeout(
    database_path: str | Path,
    *,
    limit: int | None = None,
) -> tuple[Phase6CloseoutRow, ...]:
    rows: list[Phase6CloseoutRow] = []
    for item in load_remaining_phase6_semantics(database_path, limit=limit):
        if item.is_covered:
            continue
        status, reason = _closeout_status(item)
        gap = item.gap
        rows.append(
            Phase6CloseoutRow(
                skill_rank_id=gap.skill_rank_id,
                coefficient_number=gap.coefficient_number,
                ability_id=gap.ability_id,
                ability_name=gap.name,
                disposition=gap.disposition,
                closeout_status=status,
                reason=reason,
                signals=gap.signals,
                fragment=" ".join(str(gap.fragment or "").split()),
            )
        )
    return tuple(rows)


def summarize(rows: tuple[Phase6CloseoutRow, ...]) -> dict[str, object]:
    statuses = Counter(row.closeout_status for row in rows)
    review_reasons = Counter(row.reason for row in rows if row.closeout_status == "NEEDS_PHASE6_REVIEW")
    return {
        "rows": len(rows),
        "statuses": statuses,
        "needs_review": statuses["NEEDS_PHASE6_REVIEW"],
        "review_reasons": review_reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Conservatively classify every still-uncovered Phase 6 gap as cleanup, "
            "later-phase boundary, source blocked, ownership negative, or requiring Phase 6 review."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--samples", type=int, default=120)
    args = parser.parse_args()

    rows = load_phase6_closeout(args.database, limit=args.limit)
    summary = summarize(rows)
    statuses: Counter[str] = summary["statuses"]  # type: ignore[assignment]
    review_reasons: Counter[str] = summary["review_reasons"]  # type: ignore[assignment]

    print("\n========================================")
    print(" PHASE 6 CLOSEOUT AUDIT")
    print("========================================")
    print(f"Database:                 {args.database}")
    print(f"Still-uncovered rows:     {summary['rows']}")
    print(f"Needs Phase 6 review:     {summary['needs_review']}")

    print("\nSTATUS")
    for name, count in statuses.most_common():
        print(f"  {name:28} {count}")

    print("\nPHASE 6 REVIEW REASONS")
    for name, count in review_reasons.most_common():
        print(f"  {name:60} {count}")

    print(
        "\nNOTE: this audit is intentionally conservative. Rows are cleared only when "
        "existing evidence justifies classification cleanup, a later-phase boundary, "
        "a source block, or a known ownership negative."
    )

    ordered = sorted(
        rows,
        key=lambda row: (
            row.closeout_status != "NEEDS_PHASE6_REVIEW",
            row.reason,
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
        print(f"status={row.closeout_status}")
        print(f"reason={row.reason}")
        print(f"disposition={row.disposition}")
        if row.signals:
            print(f"signals={','.join(row.signals)}")
        if row.fragment:
            print(f"fragment={row.fragment}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
