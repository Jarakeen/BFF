from __future__ import annotations

"""Published Extreme Record for the closed U50 Magicka Recovery maximum.

The exhaustive proof remains owned by the Magicka Recovery audit suite. This
service is the stable consumer-facing projection of that closed proof into
``ExtremeRecordResult`` so UI and downstream optimizers can consume the result
without reimplementing the mechanics.
"""

from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)


class ExtremeMagickaRecoveryRecordService:
    """Expose the closed theoretical U50 Magicka Recovery record."""

    OBJECTIVE_KEY = "magicka_recovery"
    RAW_VALUE = 19492.945
    ESO_DISPLAY_VALUE = 19493

    @classmethod
    def supports(cls, objective_key: str) -> bool:
        return str(objective_key or "").strip().casefold() == cls.OBJECTIVE_KEY

    @classmethod
    def record(cls) -> ExtremeRecordResult:
        winning_build = {
            "record_kind": "theoretical_contextual_maximum",
            "game_update": "U50",
            "race": "Breton",
            "class_lines": (
                "Animal Companions",
                "Curative Runeforms",
                "Shadow",
            ),
            "active_bar": {
                "Animal Companions": 1,
                "Support": 3,
                "Minor Intellect carrier": "Arcanist's Domain",
                "Mages Guild": 0,
            },
            "armor_weight": "Light",
            "armor_traits": {"Divines": 7},
            "mundus": "The Atronach",
            "named_sets": (
                ("Robes of Alteration Mastery", 3),
                ("Hiti's Hearth", 3),
                ("Arkay's Charity", 3),
                ("Shadowrend", 1),
                ("Chokethorn", 1),
                ("Torc of Tonal Constancy", 1),
            ),
            "jewelry_traits": ("Infused", "Infused", "Infused"),
            "jewelry_enchants": (
                "Glyph of Magicka Recovery",
                "Glyph of Magicka Recovery",
                "Glyph of Magicka Recovery",
            ),
            "provisioning": "Crisp River's Ale",
            "same_build_max_magicka": 26924.736,
            "champion_points": (
                ("Refreshing Stride", 500.0),
                ("Peace of Mind", 200.0),
                ("Sustained by Suffering", 150.0),
                ("Rejuvenation", 90.0),
                ("Enlivening Overflow", 134.624),
            ),
            "pre_percent_recovery": 5184.294,
            "standing_recovery_percent": 126.0,
            "contextual_recovery_percent": 150.0,
            "total_recovery_percent": 276.0,
            "eso_display_value": cls.ESO_DISPLAY_VALUE,
        }
        coverage = ExtremeRecordSearchCoverage(
            searched=(
                "base, racial, armor, Mundus, provisioning, jewelry, and Champion Point Recovery denominator",
                "same-build Max Magicka for Enlivening Overflow",
                "legal class/subclass Recovery route frontier",
                "five-normal-plus-one-Ultimate active-bar topology",
                "Support Magicka Aid versus Mages Guild and class-line slot opportunity cost",
                "self-usable Minor Intellect skill carriers",
                "ordinary and special named gear including Mythic legality",
                "Torc of Tonal Constancy versus Willow's Path, Oakensoul, and surviving special gear challengers",
                "route-compatible conditional and scaling Recovery passives",
                "Continuous Attack conditional Recovery",
                "Emperor Domination six-Home-Keep Recovery ceiling",
            ),
            omitted=(),
            denominator_proven=True,
        )
        return ExtremeRecordResult.for_objective(
            cls.OBJECTIVE_KEY,
            raw_value=cls.RAW_VALUE,
            proof_status=ExtremeRecordProofStatus.PROVEN,
            winning_build=winning_build,
            unit="Magicka Recovery",
            runtime_prerequisites=(
                "Theoretical contextual maximum; all listed standing and contextual states must overlap at the scoring instant.",
                "Maintain Torc of Tonal Constancy's reviewed conditional Magicka Recovery branch.",
                "Keep Arcanist's Domain active for self-provided Minor Intellect while preserving one Animal Companions and three Support abilities on the five normal slots.",
                "Use a legal U50 Major Intellect potion at the scoring instant.",
                "Score within Continuous Attack's reviewed ten-minute capture window.",
            ),
            self_provided_conditions=(
                "seven Light armor pieces",
                "seven Divines with The Atronach",
                "three Infused Magicka Recovery jewelry glyphs",
                "Crisp River's Ale drink buff",
                "Animal Companions + Curative Runeforms + Shadow class route",
                "one Animal Companions skill, three Support skills, and Arcanist's Domain on the active normal bar",
                "Minor Intellect from Arcanist's Domain",
                "Major Intellect from a legal U50 potion",
                "Continuous Attack active after a qualifying Alliance War capture",
            ),
            external_conditions=(
                "Emperor Domination at six Home Keeps",
            ),
            search_coverage=coverage,
            explanation=(
                "Closed U50 Extreme Magicka Recovery theoretical contextual maximum: 19,492.945 raw, displayed as 19,493.",
                "The closed pre-percent checkpoint is 5,184.294 and the winning standing configuration contributes 126% Recovery before contextual states.",
                "Major Intellect adds 30%, Continuous Attack adds 20%, and six-Home-Keep Domination adds 100%, producing a total +276% Recovery layer.",
                "Every final-snapshot proof gate is closed with zero unresolved mechanics; runtime and external conditions remain explicit rather than being treated as always-on stats.",
            ),
        )


__all__ = ["ExtremeMagickaRecoveryRecordService"]
