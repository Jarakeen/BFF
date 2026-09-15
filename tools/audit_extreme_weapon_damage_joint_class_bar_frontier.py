from __future__ import annotations

"""Joint legal class-route + active-bar frontier for Extreme Weapon Damage.

This audit combines only already-reviewed class/subclass slot-count passives,
pure-class Class Mastery selections, and concrete legal active-bar standing skill
effects. External named buffs (potions/group providers), named gear, weapons, and
other runtime layers remain separate so named effects are not double-counted.
"""

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.character_build.character_class import CharacterClass
from services.extreme_class_configuration_service import (
    ExtremeClassConfigurationCandidate,
    ExtremeClassConfigurationService,
)
from services.extreme_class_mastery_pair_service import ExtremeClassMasteryPairService
from services.extreme_skill_standing_effect_service import ExtremeSkillStandingEffectService
from services.extreme_subclass_skill_bar_service import ExtremeSubclassSkillBarService
from services.extreme_subclass_slot_allocation_service import ExtremeSubclassSlotAllocationService

DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "weapon_damage"
DEFAULT_REFERENCES = (1000.0, 2233.3333333333, 3000.0, 6000.0, 10000.0, 15000.0)


@dataclass(frozen=True)
class _Candidate:
    reference: float
    base_class: CharacterClass
    lines: tuple[str, ...]
    pure: bool
    slot_counts: tuple[tuple[str, int], ...]
    skill_names: tuple[str, ...]
    passive_delta: float
    standing_skill_delta: float
    mastery_delta: float
    total_delta: float
    sources: tuple[str, ...]
    runtime_conditions: tuple[str, ...]


def _mastery_for(
    service: ExtremeClassMasteryPairService,
    config: ExtremeClassConfigurationCandidate,
    reference: float,
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    if not config.is_pure_class:
        return 0.0, (), ()
    row = service.best_for_class(
        config.base_class,
        OBJECTIVE,
        reference_value=reference,
    )
    if row is None or row.projected_delta is None:
        return 0.0, (), ()
    return (
        float(row.projected_delta),
        tuple(row.passive_names),
        tuple(row.conditions),
    )


def _candidate_key(row: _Candidate):
    return (
        row.total_delta,
        row.standing_skill_delta,
        row.mastery_delta,
        row.passive_delta,
        row.pure,
        row.base_class.value,
        row.lines,
        row.slot_counts,
        tuple(name.casefold() for name in row.skill_names),
    )


def _frontier_for_reference(reference: float) -> tuple[_Candidate | None, int, int]:
    bar_service = ExtremeSubclassSkillBarService(DATABASE)
    mastery_service = ExtremeClassMasteryPairService(DATABASE)
    best: _Candidate | None = None
    configurations_reviewed = 0
    legal_bars_reviewed = 0

    for config in ExtremeClassConfigurationService.all_candidates():
        configurations_reviewed += 1
        mastery_delta, mastery_sources, mastery_conditions = _mastery_for(
            mastery_service,
            config,
            reference,
        )

        allocations = ExtremeSubclassSlotAllocationService.reviewed_allocations(
            config.equipped_skill_lines,
            OBJECTIVE,
            reference_value=reference,
            include_known_zero=True,
        )
        for allocation in allocations:
            bar = bar_service.materialize(
                allocation.slot_counts,
                objective_key=OBJECTIVE,
                reference_value=reference,
            )
            if bar is None:
                continue
            legal_bars_reviewed += 1

            standing_delta, standing_sources = ExtremeSkillStandingEffectService.score_build_bars(
                bar.names,
                (),
                OBJECTIVE,
                active_bar="front",
                reference_value=reference,
            )
            passive_delta = float(allocation.projected_delta)
            total = passive_delta + float(standing_delta) + mastery_delta
            sources = tuple(
                dict.fromkeys(
                    (*allocation.reviewed_sources, *standing_sources, *mastery_sources)
                )
            )
            candidate = _Candidate(
                reference=float(reference),
                base_class=config.base_class,
                lines=config.equipped_skill_lines,
                pure=config.is_pure_class,
                slot_counts=allocation.slot_counts,
                skill_names=bar.names,
                passive_delta=passive_delta,
                standing_skill_delta=float(standing_delta),
                mastery_delta=mastery_delta,
                total_delta=total,
                sources=sources,
                runtime_conditions=mastery_conditions,
            )
            if best is None or _candidate_key(candidate) > _candidate_key(best):
                best = candidate

    return best, configurations_reviewed, legal_bars_reviewed


def main() -> int:
    print("EXTREME WEAPON DAMAGE JOINT CLASS + ACTIVE-BAR FRONTIER")
    print(f"database={DATABASE}")
    print(f"objective={OBJECTIVE}")
    print("external_named_buffs_in_scope=False")
    print("named_gear_in_scope=False")
    print("weapon_realization_in_scope=False")
    print()

    winners: list[_Candidate] = []
    unresolved: list[str] = []
    total_configurations = 0
    total_bars = 0

    for reference in DEFAULT_REFERENCES:
        winner, configuration_count, bar_count = _frontier_for_reference(reference)
        total_configurations = max(total_configurations, configuration_count)
        total_bars += bar_count
        print(f"REFERENCE={reference:.3f}")
        print(f"  configurations_reviewed={configuration_count}")
        print(f"  legal_bars_reviewed={bar_count}")
        if winner is None:
            unresolved.append(f"No legal reviewed class/bar candidate at reference {reference:g}")
            print("  winner=<none>")
            print()
            continue
        winners.append(winner)
        print(
            f"  winner class={winner.base_class.value} pure={winner.pure} "
            f"delta={winner.total_delta:.3f}"
        )
        print(f"  lines={winner.lines!r}")
        print(f"  slots={winner.slot_counts!r}")
        print(f"  skills={winner.skill_names!r}")
        print(
            f"  components passive={winner.passive_delta:.3f} "
            f"standing_skill={winner.standing_skill_delta:.3f} "
            f"class_mastery={winner.mastery_delta:.3f}"
        )
        for source in winner.sources:
            print(f"    source: {source}")
        for condition in winner.runtime_conditions:
            print(f"    runtime: {condition}")
        print()

    signatures = tuple(
        dict.fromkeys(
            (
                row.base_class.value,
                row.pure,
                row.lines,
                row.slot_counts,
                row.skill_names,
                row.sources,
                row.runtime_conditions,
            )
            for row in winners
        )
    )
    stable = bool(winners) and len(signatures) == 1

    print("FRONTIER SUMMARY")
    print(f"reference_sample_count={len(DEFAULT_REFERENCES)}")
    print(f"configurations_per_reference={total_configurations}")
    print(f"legal_bar_realizations_reviewed_total={total_bars}")
    print(f"distinct_winner_signatures={len(signatures)}")
    for signature in signatures:
        print(f"  winner_signature={signature!r}")
    print(f"joint_class_bar_reference_stable={stable}")
    print(f"unresolved_count={len(unresolved)}")
    for message in unresolved:
        print(f"  unresolved: {message}")

    closed = bool(winners) and not unresolved
    print(f"joint_class_bar_frontier_enumerated={closed}")
    print("final_weapon_damage_record_closed=False")
    print(
        "NEXT_STEP=resolve the piecewise winning class/bar formula against the exact "
        "pre-class Weapon Damage subtotal, then add external named-power state without "
        "double-counting standing Major Brutality before exact named-gear composition"
    )
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
