from __future__ import annotations

"""Close the Arcane-vs-Infused jewelry coupling for Extreme Magicka Recovery.

The proof is deliberately conservative.  It gives every Arcane substitution the
full Enlivening Overflow cap even though the three-Infused baseline already has
at least the character's canonical base Max Magicka.  If Infused still wins
under that favorable bound, the Arcane branch is globally dominated without
requiring a final same-build Max Magicka witness first.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.base_character_state import BASE_MAX_MAGICKA
from minmax.conditional_recovery import (
    ENLIVENING_OVERFLOW_MAX_BONUS,
    ENLIVENING_OVERFLOW_MAX_MAGICKA_PERCENT,
    enlivening_overflow_recovery_bonus,
)
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.stat_ids import StatId
from services.extreme_recovery_jewelry_projection_service import (
    ExtremeRecoveryJewelryProjectionService,
)

OBJECTIVE = "magicka_recovery"
JEWELRY_SLOTS = 3


@dataclass(frozen=True)
class JewelryVariantBound:
    arcane_slots: int
    infused_slots: int
    direct_recovery: float
    enlivening_upper_bound: float
    total_recovery_upper_bound: float
    dominated_by_three_infused: bool


def enlivening_cap_requirement() -> float:
    return float(ENLIVENING_OVERFLOW_MAX_BONUS) / float(
        ENLIVENING_OVERFLOW_MAX_MAGICKA_PERCENT
    )


def conservative_three_infused_total(
    *,
    three_infused_recovery: float,
    baseline_max_magicka: float = BASE_MAX_MAGICKA,
) -> float:
    baseline_enlivening = float(enlivening_overflow_recovery_bonus(int(baseline_max_magicka)))
    return float(three_infused_recovery) + baseline_enlivening


def arcane_variant_upper_bound(
    *,
    arcane_slots: int,
    base_glyph_recovery: float,
    infused_glyph_recovery: float,
    three_infused_conservative_total: float,
) -> JewelryVariantBound:
    if arcane_slots < 0 or arcane_slots > JEWELRY_SLOTS:
        raise ValueError(f"arcane_slots must be between 0 and {JEWELRY_SLOTS}")

    infused_slots = JEWELRY_SLOTS - arcane_slots
    direct = (
        float(arcane_slots) * float(base_glyph_recovery)
        + float(infused_slots) * float(infused_glyph_recovery)
    )
    enlivening_upper = float(ENLIVENING_OVERFLOW_MAX_BONUS)
    total_upper = direct + enlivening_upper
    return JewelryVariantBound(
        arcane_slots=arcane_slots,
        infused_slots=infused_slots,
        direct_recovery=direct,
        enlivening_upper_bound=enlivening_upper,
        total_recovery_upper_bound=total_upper,
        dominated_by_three_infused=total_upper < float(three_infused_conservative_total) - 1e-9,
    )


def _arcane_per_slot(repository: JewelryTraitRepository) -> float | None:
    effects = repository.get_static_effects("arcane", quality="Gold", level="CP160")
    values = [float(effect.value) for effect in effects if effect.stat is StatId.MAX_MAGICKA]
    if len(values) != 1:
        return None
    return values[0]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=str(ROOT / "data" / "eso.db"))
    return parser


def main() -> int:
    database = Path(_parser().parse_args().database)
    glyph_repository = JewelryGlyphEffectRepository(database)
    trait_repository = JewelryTraitRepository(database)
    projection = ExtremeRecoveryJewelryProjectionService(
        glyph_repository,
        trait_repository,
    ).build(OBJECTIVE)

    unresolved: list[str] = list(projection.unresolved)
    arcane_per_slot = _arcane_per_slot(trait_repository)
    if arcane_per_slot is None:
        unresolved.append("CP160 Gold Arcane Max Magicka value unresolved")

    base_glyph = projection.base_flat_per_slot
    infused_glyph = projection.infused_flat_per_slot
    three_infused = projection.three_slot_infused_flat
    if base_glyph is None or infused_glyph is None or three_infused is None:
        unresolved.append("Magicka Recovery jewelry glyph projection incomplete")

    cap_requirement = enlivening_cap_requirement()
    baseline_enlivening = float(enlivening_overflow_recovery_bonus(int(BASE_MAX_MAGICKA)))
    conservative_total = (
        conservative_three_infused_total(three_infused_recovery=float(three_infused))
        if three_infused is not None
        else 0.0
    )

    variants: tuple[JewelryVariantBound, ...] = ()
    if base_glyph is not None and infused_glyph is not None and three_infused is not None:
        variants = tuple(
            arcane_variant_upper_bound(
                arcane_slots=count,
                base_glyph_recovery=float(base_glyph),
                infused_glyph_recovery=float(infused_glyph),
                three_infused_conservative_total=conservative_total,
            )
            for count in range(1, JEWELRY_SLOTS + 1)
        )

    all_arcane_dominated = bool(variants) and all(row.dominated_by_three_infused for row in variants)
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    closed = projection.denominator_proven and arcane_per_slot is not None and all_arcane_dominated and not unique_unresolved

    print("EXTREME MAGICKA RECOVERY ENLIVENING / JEWELRY FRONTIER")
    print(f"database={database}")
    print(f"objective={OBJECTIVE}")
    print()
    print("ENLIVENING")
    print(f"cap={ENLIVENING_OVERFLOW_MAX_BONUS}")
    print(f"max_magicka_percent={ENLIVENING_OVERFLOW_MAX_MAGICKA_PERCENT:.6f}")
    print(f"exact_cap_requirement={cap_requirement:.3f}")
    print(f"canonical_base_max_magicka={BASE_MAX_MAGICKA:.3f}")
    print(f"base_only_enlivening={baseline_enlivening:.3f}")
    print(f"remaining_enlivening_headroom={ENLIVENING_OVERFLOW_MAX_BONUS - baseline_enlivening:.3f}")
    print()
    print("JEWELRY")
    print(f"recovery_glyph={projection.strongest_glyph_name!r}")
    print(f"base_recovery_per_slot={float(base_glyph or 0.0):.3f}")
    print(f"infused_percent={float(projection.infused_percent or 0.0):.3f}")
    print(f"infused_recovery_per_slot={float(infused_glyph or 0.0):.3f}")
    print(f"three_infused_direct_recovery={float(three_infused or 0.0):.3f}")
    print(f"arcane_max_magicka_per_slot={float(arcane_per_slot or 0.0):.3f}")
    print(f"three_infused_conservative_total_with_base_only_enlivening={conservative_total:.3f}")
    print()
    print("ARCANE SUBSTITUTION UPPER BOUNDS")
    for row in variants:
        margin = conservative_total - row.total_recovery_upper_bound
        print(
            f"arcane_slots={row.arcane_slots} infused_slots={row.infused_slots} "
            f"direct_recovery={row.direct_recovery:.3f} "
            f"enlivening_upper_bound={row.enlivening_upper_bound:.3f} "
            f"total_upper_bound={row.total_recovery_upper_bound:.3f} "
            f"three_infused_margin={margin:.3f} "
            f"dominated={row.dominated_by_three_infused}"
        )
    print()
    print("PROOF GATES")
    print(f"enlivening_exact_cap_requirement_proven={abs(cap_requirement - 30000.0) <= 1e-9}")
    print(f"jewelry_projection_denominator_proven={projection.denominator_proven}")
    print(f"arcane_static_value_proven={arcane_per_slot is not None}")
    print(f"all_arcane_substitutions_dominated={all_arcane_dominated}")
    print(f"unresolved_count={len(unique_unresolved)}")
    for item in unique_unresolved:
        print(f"  unresolved: {item}")
    print(f"magicka_recovery_jewelry_frontier_closed={closed}")
    if closed:
        print("NEXT_STEP=build the three-Infused same-build Max Magicka witness and score Enlivening exactly, then compose the legal CP total into the pre-class Recovery reference")
    else:
        print("NEXT_STEP=close only the reported Enlivening/jewelry blockers")
    return 0 if closed else 2


if __name__ == "__main__":
    raise SystemExit(main())
