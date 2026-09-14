from __future__ import annotations

"""Published Extreme Record for the closed U50 Health Recovery maximum.

The exhaustive proof remains owned by the Health Recovery denominator/runtime audit
suite.  This service is the stable consumer-facing projection of that closed proof
into ``ExtremeRecordResult`` so UI and downstream optimizers can consume the result
without reimplementing the mechanics.
"""

from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)


class ExtremeHealthRecoveryRecordService:
    """Expose the closed theoretical stochastic U50 Health Recovery record."""

    OBJECTIVE_KEY = "health_recovery"
    RAW_VALUE = 22576.212
    ESO_DISPLAY_VALUE = 22577

    @classmethod
    def supports(cls, objective_key: str) -> bool:
        return str(objective_key or "").strip().casefold() == cls.OBJECTIVE_KEY

    @classmethod
    def record(cls) -> ExtremeRecordResult:
        winning_build = {
            "record_kind": "theoretical_stochastic_maximum",
            "game_update": "U50",
            "race": "Khajiit",
            "armor_weight": "Heavy",
            "armor_traits": {"Divines": 7, "Invigorating": 0},
            "mundus": "The Steed",
            "named_sets": (
                ("Beekeeper's Gear", 5),
                ("Adamant Lurker", 5),
                ("Baron Zaudrus", 2),
            ),
            "weapon_type": "Inferno Staff",
            "weapon_trait": "Decisive",
            "jewelry_traits": ("Infused", "Infused", "Infused"),
            "jewelry_enchants": (
                "Glyph of Health Recovery",
                "Glyph of Health Recovery",
                "Glyph of Health Recovery",
            ),
            "provisioning": "Fresh Dragon's-Tongue Ale",
            "same_build_max_magicka": 25932.744,
            "champion_points": (
                ("Strategic Reserve", 1500.0),
                ("Peace of Mind", 200.0),
                ("Sustained by Suffering", 150.0),
                ("Rejuvenation", 90.0),
                ("Enlivening Overflow", 129.66372),
            ),
            "eso_display_value": cls.ESO_DISPLAY_VALUE,
        }
        coverage = ExtremeRecordSearchCoverage(
            searched=(
                "race Health Recovery denominator",
                "legal class-route signatures and Class Mastery",
                "seven-Heavy armor trait and Steed Mundus frontier",
                "jewelry traits and Health Recovery glyphs",
                "food/drink provisioning",
                "potion-backed Major Fortitude",
                "ordinary and special named gear",
                "Destruction Staff physical realization",
                "slottable and non-slottable Champion Points",
                "same-build Max Magicka for Enlivening Overflow",
                "runtime compatibility",
                "Baron Zaudrus status-application opportunity ceiling",
                "Decisive stochastic Ultimate opportunity ceiling",
            ),
            omitted=(),
            denominator_proven=True,
        )
        return ExtremeRecordResult.for_objective(
            cls.OBJECTIVE_KEY,
            raw_value=cls.RAW_VALUE,
            proof_status=ExtremeRecordProofStatus.PROVEN,
            winning_build=winning_build,
            unit="Health Recovery",
            runtime_prerequisites=(
                "Theoretical stochastic maximum; this is not a deterministic gameplay claim.",
                "Score at the reviewed low-health Adamant Lurker / Elder Dragon boundary.",
                "Spend a reviewed 250-Ultimate Destruction Staff Ultimate for Booming Voice.",
                "Return Strategic Reserve to the reviewed 500-Ultimate state inside the scoring window.",
                "Realize the all-procs Decisive ceiling and the Force Shock status-roll ceiling needed for 18 Baron Zaudrus procs.",
                "Maintain the reviewed Champion Point runtime conditions at the scoring instant.",
            ),
            self_provided_conditions=(
                "Major Fortitude from a legal U50 potion",
                "Fresh Dragon's-Tongue Ale drink buff",
                "seven Heavy armor pieces",
                "seven Divines with The Steed",
                "three Infused Health Recovery jewelry glyphs",
                "Inferno Staff with Decisive",
            ),
            external_conditions=(
                "Emperor Domination at six Home Keeps",
            ),
            search_coverage=coverage,
            explanation=(
                "Closed U50 Extreme Health Recovery theoretical maximum: 22,576.212 raw, displayed as 22,577 after ESO ceiling rounding.",
                "The winning active-snapshot gear realization is Beekeeper's Gear 5pc + Adamant Lurker 5pc + Baron Zaudrus 2pc with a Decisive Inferno Staff.",
                "The same build reaches 25,932.744 Max Magicka, so Enlivening Overflow contributes 129.664 rather than its 150-point cap.",
                "Every final-record proof gate is closed with zero unresolved mechanics; stochastic Ultimate/status ceilings remain explicit prerequisites rather than deterministic claims.",
            ),
        )


__all__ = ["ExtremeHealthRecoveryRecordService"]
