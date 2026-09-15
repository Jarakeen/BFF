from __future__ import annotations

"""Joint legal class-route + active-bar frontier for Extreme Weapon Damage.

This audit combines only already-reviewed class/subclass slot-count passives,
pure-class Class Mastery selections, and concrete legal active-bar standing skill
effects. External named buffs (potions/group providers), named gear, weapons, and
other runtime layers remain separate so named effects are not double-counted.

The expensive structural work is cached by unique equipped-line set. For the
Weapon Damage objective, the reviewed subclass slot-count contribution is flat
(Expert Mage) and the only reviewed standing-skill contribution is Major
Brutality at a fixed 20% of the supplied reference. Therefore legal bar identity
is invariant across positive reference values: materialize each unique bar once
at reference=1, preserve its flat passive term and standing-skill coefficient,
then rescale only the coefficient and Class Mastery contribution per checkpoint.
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
TEMPLATE_REFERENCE = 1.0


@dataclass(frozen=True)
class _BarTemplate:
    lines: tuple[str, ...]
    slot_counts: tuple[tuple[str, int], ...]
    skill_names: tuple[str, ...]
    passive_delta: float
    passive_sources: tuple[str, ...]
    standing_ratio: float
    standing_sources: tuple[str, ...]


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


def _build_bar_templates(
    configurations: tuple[ExtremeClassConfigurationCandidate, ...],
) -> tuple[dict[tuple[str, ...], tuple[_BarTemplate, ...]], int]:
    """Materialize each unique line-set/allocation only once.

    The original audit repeated this work for every base-class configuration and
    every reference value. Many base classes can legally produce the same equipped
    line set, so that multiplied identical NamedBuffResolution work tens of
    thousands of times without adding proof coverage.
    """

    bar_service = ExtremeSubclassSkillBarService(DATABASE)
    unique_line_sets = tuple(
        sorted({config.equipped_skill_lines for config in configurations})
    )
    templates: dict[tuple[str, ...], tuple[_BarTemplate, ...]] = {}
    materializations = 0

    for lines in unique_line_sets:
        rows: list[_BarTemplate] = []
        allocations = ExtremeSubclassSlotAllocationService.reviewed_allocations(
            lines,
            OBJECTIVE,
            reference_value=TEMPLATE_REFERENCE,
            include_known_zero=True,
        )
        for allocation in allocations:
            bar = bar_service.materialize(
                allocation.slot_counts,
                objective_key=OBJECTIVE,
                reference_value=TEMPLATE_REFERENCE,
            )
            if bar is None:
                continue
            materializations += 1
            standing_at_one, standing_sources = ExtremeSkillStandingEffectService.score_build_bars(
                bar.names,
                (),
                OBJECTIVE,
                active_bar="front",
                reference_value=TEMPLATE_REFERENCE,
            )
            rows.append(
                _BarTemplate(
                    lines=lines,
                    slot_counts=allocation.slot_counts,
                    skill_names=bar.names,
                    passive_delta=float(allocation.projected_delta),
                    passive_sources=tuple(allocation.reviewed_sources),
                    standing_ratio=float(standing_at_one),
                    standing_sources=tuple(standing_sources),
                )
            )
        templates[lines] = tuple(rows)

    return templates, materializations


def _frontier_for_reference(
    reference: float,
    *,
    configurations: tuple[ExtremeClassConfigurationCandidate, ...],
    templates: dict[tuple[str, ...], tuple[_BarTemplate, ...]],
    mastery_service: ExtremeClassMasteryPairService,
) -> tuple[_Candidate | None, int]:
    best: _Candidate | None = None
    candidate_rows_reviewed = 0

    for config in configurations:
        mastery_delta, mastery_sources, mastery_conditions = _mastery_for(
            mastery_service,
            config,
            reference,
        )
        for template in templates.get(config.equipped_skill_lines, ()):
            candidate_rows_reviewed += 1
            standing_delta = template.standing_ratio * float(reference)
            total = template.passive_delta + standing_delta + mastery_delta
            sources = tuple(
                dict.fromkeys(
                    (
                        *template.passive_sources,
                        *template.standing_sources,
                        *mastery_sources,
                    )
                )
            )
            candidate = _Candidate(
                reference=float(reference),
                base_class=config.base_class,
                lines=config.equipped_skill_lines,
                pure=config.is_pure_class,
                slot_counts=template.slot_counts,
                skill_names=template.skill_names,
                passive_delta=template.passive_delta,
                standing_skill_delta=standing_delta,
                mastery_delta=mastery_delta,
                total_delta=total,
                sources=sources,
                runtime_conditions=mastery_conditions,
            )
            if best is None or _candidate_key(candidate) > _candidate_key(best):
                best = candidate

    return best, candidate_rows_reviewed


def main() -> int:
    configurations = ExtremeClassConfigurationService.all_candidates()
    templates, structural_materializations = _build_bar_templates(configurations)
    mastery_service = ExtremeClassMasteryPairService(DATABASE)

    print("EXTREME WEAPON DAMAGE JOINT CLASS + ACTIVE-BAR FRONTIER")
    print(f"database={DATABASE}")
    print(f"objective={OBJECTIVE}")
    print("external_named_buffs_in_scope=False")
    print("named_gear_in_scope=False")
    print("weapon_realization_in_scope=False")
    print("structural_bar_cache=True")
    print(f"configurations_reviewed={len(configurations)}")
    print(f"unique_line_sets={len(templates)}")
    print(f"structural_bar_materializations={structural_materializations}")
    print()

    winners: list[_Candidate] = []
    unresolved: list[str] = []
    candidate_rows_per_reference = 0

    for reference in DEFAULT_REFERENCES:
        winner, candidate_rows = _frontier_for_reference(
            reference,
            configurations=configurations,
            templates=templates,
            mastery_service=mastery_service,
        )
        candidate_rows_per_reference = max(candidate_rows_per_reference, candidate_rows)
        print(f"REFERENCE={reference:.3f}")
        print(f"  candidate_rows_reviewed={candidate_rows}")
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
    print(f"candidate_rows_per_reference={candidate_rows_per_reference}")
    print(f"structural_bar_materializations_once={structural_materializations}")
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
