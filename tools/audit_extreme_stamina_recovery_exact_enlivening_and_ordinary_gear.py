from __future__ import annotations

"""Close exact Enlivening and ordinary named gear for Extreme Stamina Recovery."""

import argparse
from dataclasses import dataclass, replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_STAMINA_RECOVERY, BaseCharacterCalculator, ResourceInputs
from minmax.champion_point_static_repository import ChampionPointStaticRepository
from minmax.effects import EffectOperation
from minmax.gear_set_repository import GearSetRepository
from minmax.passive_math import undaunted_mettle_resource_percent
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId
from services.extreme_armor_weight_filtered_slot_eligibility_service import ExtremeArmorWeightFilteredSlotEligibilityService
from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointService
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveBreakpointEvidence,
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalogService
from services.extreme_max_resource_ordinary_named_gear_search_service import ExtremeMaxResourceOrdinaryNamedGearSearchService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityService
from services.extreme_recovery_jewelry_projection_service import ExtremeRecoveryJewelryProjectionService
from services.extreme_recovery_provisioning_projection_service import ExtremeRecoveryProvisioningProjectionService
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from tools.audit_extreme_health_recovery_final_record import _armor_magicka_glyph_flat, _provisioning_magicka
from tools.audit_extreme_magicka_recovery_same_build_enlivening import exact_enlivening_value

OBJECTIVE = "stamina_recovery"
RESOURCE_OBJECTIVE = "max_magicka"
STANDING_MULTIPLIER = 1.96
OTHER_CP = 150.0 + 90.0


@dataclass(frozen=True)
class PairScore:
    direct_recovery: float
    max_magicka_flat: float
    optimistic_effective_recovery: float
    ordinary: bool


class _Search(ExtremeMaxResourceOrdinaryNamedGearSearchService):
    SUPPORTED_OBJECTIVES = frozenset((*ExtremeMaxResourceOrdinaryNamedGearSearchService.SUPPORTED_OBJECTIVES, OBJECTIVE))

    def __init__(self, *, pair_scores: dict[tuple[int, int], PairScore], **kwargs) -> None:
        super().__init__(**kwargs)
        self.pair_scores = dict(pair_scores)

    def _ordinary_exact_delta(self, evidence, objective_key: str) -> float | None:  # type: ignore[override]
        row = self.pair_scores.get((int(evidence.set_id), int(evidence.piece_count)))
        if row is None or not row.ordinary:
            return None
        return float(row.optimistic_effective_recovery)

    def _objective_effect_signature(self, evidence, objective_key: str):  # type: ignore[override]
        row = self.pair_scores.get((int(evidence.set_id), int(evidence.piece_count)))
        if row is None or not row.ordinary:
            return ()
        return (("stamina_recovery", round(row.direct_recovery, 9)), ("max_magicka", round(row.max_magicka_flat, 9)))


def _ordinary_flat(evidence: ExtremeGearSetObjectiveBreakpointEvidence | None, objective_key: str) -> float | None:
    if evidence is None or evidence.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT:
        return 0.0
    return ExtremeMaxResourceOrdinaryNamedGearSearchService._ordinary_exact_delta(evidence, objective_key)


def _pair_scores(recovery, magicka, conversion: float):
    r_by = {(int(row.set_id), int(row.piece_count)): row for row in recovery.evidence}
    m_by = {(int(row.set_id), int(row.piece_count)): row for row in magicka.evidence}
    scores: dict[tuple[int, int], PairScore] = {}
    merged = []
    for pair in sorted(set(r_by) | set(m_by)):
        r = r_by.get(pair)
        m = m_by.get(pair)
        direct = _ordinary_flat(r, OBJECTIVE)
        mm = _ordinary_flat(m, RESOURCE_OBJECTIVE)
        ordinary = direct is not None and mm is not None
        d = float(direct or 0.0)
        f = float(mm or 0.0)
        optimistic = d + f * conversion
        scores[pair] = PairScore(d, f, optimistic, ordinary)
        base = r or m
        assert base is not None
        status = ExtremeGearSetObjectiveRelevance.RELEVANT if ordinary and optimistic > 1e-12 else ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT if ordinary else ExtremeGearSetObjectiveRelevance.UNRESOLVED
        candidate = replace(base.candidate, objective_key=OBJECTIVE, reviewed_delta=optimistic, unresolved=(() if ordinary else base.candidate.unresolved))
        merged.append(replace(base, objective_key=OBJECTIVE, status=status, reviewed_delta=optimistic, candidate=candidate, search_state_rule=None))
    merged.sort(key=lambda row: (row.set_name.casefold(), row.set_id, row.piece_count))
    return scores, ExtremeGearSetObjectiveRelevanceCatalog(objective_key=OBJECTIVE, evidence=tuple(merged), unresolved=())


def _arcane_supremacy(database: Path) -> tuple[float, int | None, bool, tuple[str, ...]]:
    repository = ChampionPointStaticRepository(database)
    record = repository.get("Arcane Supremacy")
    if record is None:
        return 0.0, None, False, ("Arcane Supremacy missing",)
    effects, unresolved = repository.resolve(record.name, record.max_points)
    flat = sum(float(effect.value) for effect in effects if effect.stat is StatId.MAX_MAGICKA and effect.operation is EffectOperation.ADD)
    return flat, record.discipline_index, record.is_slottable, tuple(unresolved)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    database = Path(_parser().parse_args().database)
    unresolved: list[str] = []

    armor_glyph = _armor_magicka_glyph_flat(database)
    if armor_glyph is None:
        unresolved.append("seven-piece Max Magicka armor glyph value unresolved")
        armor_glyph = 0.0
    food_flat, food_percent, food_unresolved = _provisioning_magicka(database, "Hagraven's Tonic")
    unresolved.extend(food_unresolved)
    arcane_flat, arcane_disc, arcane_slottable, arcane_unresolved = _arcane_supremacy(database)
    unresolved.extend(arcane_unresolved)
    existing_recovery_slots = 1 if arcane_disc == 2 else 2 if arcane_disc == 3 else 0
    arcane_slot_legal = bool(arcane_slottable and arcane_disc is not None and existing_recovery_slots + 1 <= 4)
    if not arcane_slot_legal:
        unresolved.append("Arcane Supremacy slot legality unresolved")

    race_magicka = float(RaceRepository(database).get_stat_map_by_name("Bosmer").get("max_magicka", 0.0))
    undaunted = undaunted_mettle_resource_percent(1)
    trace = BaseCharacterCalculator().max_magicka(ResourceInputs(item_flat=float(armor_glyph), food_flat=float(food_flat), champion_flat=float(arcane_flat if arcane_slot_legal else 0.0), race_flat=race_magicka, other_percent=float(undaunted + food_percent)))
    max_magicka = float(trace.raw_value)
    enlivening = exact_enlivening_value(max_magicka)
    exact_cp = enlivening + OTHER_CP

    jewelry = ExtremeRecoveryJewelryProjectionService(JewelryGlyphEffectRepository(database), JewelryTraitRepository(database)).build(OBJECTIVE)
    provisioning = ExtremeRecoveryProvisioningProjectionService.build(database, objective_key=OBJECTIVE)
    drink = provisioning.drink
    if drink is None:
        unresolved.append("Stamina Recovery drink winner missing")
    base_pregear = float(BASE_STAMINA_RECOVERY) + 258.0 + 507.47 + float(jewelry.three_slot_infused_flat or 0.0) + float(drink.delta if drink else 0.0) + exact_cp

    repository = GearSetRepository(database)
    breakpoints = ExtremeGearSetBonusBreakpointService(repository).build()
    topology = ExtremeGearSetTopologyCatalogService(repository).build()
    raw = ExtremeNamedGearSetSlotEligibilityService(database).build()
    filtered = ExtremeArmorWeightFilteredSlotEligibilityService.build(database, raw, required_armor_weight="Medium")
    recovery = ExtremeGearSetObjectiveRelevanceService(repository).build(OBJECTIVE, breakpoints)
    magicka = ExtremeGearSetObjectiveRelevanceService(repository).build(RESOURCE_OBJECTIVE, breakpoints)
    conversion = 0.005 * (1.0 + undaunted)
    scores, merged = _pair_scores(recovery, magicka, conversion)
    search = _Search(breakpoints=breakpoints, eligibility=filtered.catalog, relevance=merged, pair_scores=scores).search(topology)
    winners = tuple(row for row in search.topologies if row.winner_found and row.best_exact_flat_delta is not None)
    optimistic_best = max((float(row.best_exact_flat_delta) for row in winners), default=0.0)
    realizations = tuple(realization for row in winners if abs(float(row.best_exact_flat_delta or 0.0) - optimistic_best) <= 1e-9 for realization in row.realizations)
    remaining_headroom = max(0.0, 150.0 - enlivening)
    exact_rows = []
    for realization in realizations:
        direct = 0.0
        mm_flat = 0.0
        for set_id, count in zip(realization.set_ids, realization.counts):
            pair = scores.get((int(set_id), int(count)))
            if pair is not None:
                direct += pair.direct_recovery
                mm_flat += pair.max_magicka_flat
        enlivening_gain = min(remaining_headroom, mm_flat * conversion)
        exact_rows.append((direct + enlivening_gain, direct, mm_flat, enlivening_gain, realization))
    exact_rows.sort(key=lambda row: (-row[0], row[4].set_ids, row[4].counts))
    exact_winner = exact_rows[0] if exact_rows else None
    exact_best = float(exact_winner[0]) if exact_winner else 0.0
    bound_reached = bool(exact_winner and abs(exact_best - optimistic_best) <= 1e-9)
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    ordinary_closed = bool(filtered.denominator_proven and search.ordinary_denominator_proven and realizations and bound_reached and not unique_unresolved)
    names = {int(row.set_id): row.name for row in filtered.catalog.sets}

    print("EXTREME STAMINA RECOVERY EXACT ENLIVENING + ORDINARY GEAR AUDIT")
    print(f"database={database}")
    print(f"bosmer_max_magicka_flat={race_magicka:.3f}")
    print(f"armor_magicka_glyph_flat={armor_glyph:.3f}")
    print(f"hagravens_tonic_max_magicka_flat={food_flat:.3f}")
    print(f"arcane_supremacy_flat={arcane_flat:.3f}")
    print(f"undaunted_percent={undaunted:.6f}")
    print(f"same_build_max_magicka_raw={max_magicka:.3f}")
    print(f"same_build_max_magicka_display={trace.final_value}")
    print(f"exact_enlivening={enlivening:.3f}")
    print(f"exact_cp_total={exact_cp:.3f}")
    print(f"base_pregear_recovery={base_pregear:.3f}")
    print()
    print("ORDINARY NAMED GEAR")
    print(f"optimistic_effective_recovery_best={optimistic_best:.3f}")
    print(f"special_or_nonflat_pairs={len(search.special_or_nonflat_pairs)}")
    if exact_winner is not None:
        exact, direct, mm_flat, enlivening_gain, realization = exact_winner
        sets = tuple((names.get(int(set_id), str(set_id)), int(count)) for set_id, count in zip(realization.set_ids, realization.counts))
        print(f"winner_sets={sets!r}")
        print(f"winner_direct_recovery={direct:.3f}")
        print(f"winner_max_magicka_flat={mm_flat:.3f}")
        print(f"winner_enlivening_gain={enlivening_gain:.3f}")
        print(f"winner_effective_prepercent={exact:.3f}")
        print(f"standing_final_gain={exact * STANDING_MULTIPLIER:.3f}")
        print(f"standing_recovery_with_ordinary_gear={(base_pregear + exact) * STANDING_MULTIPLIER:.3f}")
        print("assignments=" + repr(tuple((a.slot, names.get(int(a.set_id), str(a.set_id)), a.weapon_type) for a in realization.assignments)))
    print()
    print("PROOF GATES")
    print(f"arcane_supremacy_slot_legal={arcane_slot_legal}")
    print(f"medium_armor_physical_filter_proven={filtered.denominator_proven}")
    print(f"ordinary_search_denominator_proven={search.ordinary_denominator_proven}")
    print(f"optimistic_bound_reached_by_exact_realization={bound_reached}")
    print(f"unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"exact_enlivening_and_ordinary_gear_closed={ordinary_closed}")
    print("NEXT_STEP=screen the reported special/non-flat gear pairs against the ordinary incumbent, then compose Major Endurance + Continuous Attack + Battle Rush + Domination")
    return 0 if ordinary_closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
