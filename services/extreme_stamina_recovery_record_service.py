from __future__ import annotations

"""Published Extreme Record for the closed U50 Stamina Recovery maximum.

The exhaustive proof remains owned by the Stamina Recovery audit suite. This
service is the stable consumer-facing projection of that closed proof into
``ExtremeRecordResult`` so UI and downstream optimizers can consume the result
without reimplementing the mechanics.
"""

from services.extreme_record_result import (
    ExtremeRecordProofStatus,
    ExtremeRecordResult,
    ExtremeRecordSearchCoverage,
)


class ExtremeStaminaRecoveryRecordService:
    """Expose the closed theoretical U50 Stamina Recovery record."""

    OBJECTIVE_KEY = "stamina_recovery"
    RAW_VALUE = 16957.086
    ESO_DISPLAY_VALUE = 16958

    @classmethod
    def supports(cls, objective_key: str) -> bool:
        return str(objective_key or "").strip().casefold() == cls.OBJECTIVE_KEY

    @classmethod
    def record(cls) -> ExtremeRecordResult:
        winning_build = {
            "record_kind": "theoretical_contextual_maximum",
            "game_update": "U50",
            "race": "Bosmer",
            "class_lines": (
                "Animal Companions",
                "Curative Runeforms",
                "Shadow",
            ),
            "active_bar": {
                "Animal Companions": 1,
                "Minor Endurance carrier": "Arcanist's Domain",
            },
            "armor_weight": "Medium",
            "armor_traits": {"Divines": 7},
            "mundus": "The Serpent",
            "named_sets": (
                ("Jailbreaker", 5),
                ("Coward's Gear", 5),
                ("Bloodspawn", 1),
                ("Torc of Tonal Constancy", 1),
            ),
            "weapon_type": "Two-Handed Sword",
            "jewelry_traits": ("Infused", "Infused", "Infused"),
            "jewelry_enchants": (
                "Glyph of Stamina Recovery",
                "Glyph of Stamina Recovery",
                "Glyph of Stamina Recovery",
            ),
            "provisioning": "Hagraven's Tonic",
            "same_build_max_magicka": 17638.656,
            "champion_points": (
                ("Sustained by Suffering", 150.0),
                ("Rejuvenation", 90.0),
                ("Enlivening Overflow", 88.193),
            ),
            "pre_percent_recovery": 4509.863,
            "standing_recovery_percent": 96.0,
            "contextual_recovery_percent": 180.0,
            "total_recovery_percent": 276.0,
            "eso_display_value": cls.ESO_DISPLAY_VALUE,
        }
        coverage = ExtremeRecordSearchCoverage(
            searched=(
                "base, racial, armor, Mundus, provisioning, jewelry, and Champion Point Recovery denominator",
                "same-build Max Magicka for Enlivening Overflow",
                "legal class/subclass Recovery route frontier",
                "five-normal-plus-one-Ultimate active-bar topology",
                "self-usable Minor Endurance skill carriers",
                "ordinary and special named gear including Mythic legality",
                "Torc of Tonal Constancy versus Prowler's Talisman, Lustrous Soulwell, Oakensoul, Twice-Born Star, Bastion, and remaining special gear challengers",
                "Two-Handed physical realization compatible with Battle Rush",
                "route-compatible conditional and scaling Recovery passives",
                "Continuous Attack conditional Recovery",
                "Battle Rush conditional Recovery",
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
            unit="Stamina Recovery",
            runtime_prerequisites=(
                "Theoretical contextual maximum; all listed standing and contextual states must overlap at the scoring instant.",
                "Maintain Torc of Tonal Constancy's reviewed conditional Stamina Recovery branch.",
                "Keep Arcanist's Domain active for self-provided Minor Endurance while preserving at least one Animal Companions ability on the legal active bar.",
                "Use a legal U50 Major Endurance potion at the scoring instant.",
                "Score within Continuous Attack's reviewed capture window.",
                "Trigger Battle Rush by killing an enemy with the equipped Two-Handed weapon before the scoring instant.",
            ),
            self_provided_conditions=(
                "seven Medium armor pieces",
                "seven Divines with The Serpent",
                "three Infused Stamina Recovery jewelry glyphs",
                "Hagraven's Tonic drink buff",
                "Animal Companions + Curative Runeforms + Shadow class route",
                "one Animal Companions skill and Arcanist's Domain on the legal active bar",
                "Minor Endurance from Arcanist's Domain",
                "Major Endurance from a legal U50 potion",
                "Continuous Attack active after a qualifying Alliance War capture",
                "Battle Rush active after a qualifying Two-Handed weapon kill",
            ),
            external_conditions=(
                "Emperor Domination at six Home Keeps",
            ),
            search_coverage=coverage,
            explanation=(
                "Closed U50 Extreme Stamina Recovery theoretical contextual maximum: 16,957.086 raw, displayed as 16,958.",
                "The closed pre-percent checkpoint is 4,509.863 and the winning standing configuration contributes 96% Recovery before contextual states.",
                "Major Endurance adds 30%, Continuous Attack adds 20%, Battle Rush adds 30%, and six-Home-Keep Domination adds 100%, producing a total +276% Recovery layer.",
                "Every final-snapshot proof gate is closed with zero unresolved mechanics; runtime and external conditions remain explicit rather than being treated as always-on stats.",
            ),
        )


__all__ = ["ExtremeStaminaRecoveryRecordService"]
