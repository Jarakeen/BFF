from __future__ import annotations

"""Runtime compatibility facts for the proven Extreme Health Recovery route.

This layer does not score the final record. It records whether already-reviewed
conditions can coexist in one legal scoring moment and identifies branches that
require an alternate provisioning/search state rather than silently stacking every
independent component maximum.
"""

from dataclasses import dataclass
from enum import Enum
import math

from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from services.champion_point_loadout_service import ChampionPointLoadoutCandidate
from services.eso_character_progression_contract import ULTIMATE_RULES
from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeRecoverySpecialBranch,
)


class ExtremeHealthRecoveryCompatibility(str, Enum):
    COMPATIBLE = "compatible"
    ALTERNATE_PROVISIONING = "alternate_provisioning"
    REDUNDANT_NAMED_BUFF = "redundant_named_buff"
    SEARCH_STATE_MUTATION = "search_state_mutation"
    NUMERIC_EQUIPMENT_PROOF = "numeric_equipment_proof"
    RUNTIME_PROOF_REQUIRED = "runtime_proof_required"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class ExtremeHealthRecoveryRuntimeState:
    low_health_boundary: bool = True
    booming_voice_window: bool = True
    home_keeps: int = 6
    continuous_attack_active: bool = True
    heavy_armor_pieces: int = 7
    major_fortitude_active: bool = True
    provisioning_kind: str = "drink"
    standing_still: bool = True
    in_combat: bool = True
    recent_enemy_death: bool = True
    recent_ultimate_cast: bool = True
    resolve_cast_active: bool = True
    score_seconds: float = 24.999
    booming_voice_cast_seconds: float = 0.0
    booming_voice_delay_seconds: float = 15.0
    booming_voice_duration_seconds: float = 10.0
    starting_ultimate: float = 500.0
    booming_voice_ultimate_spend: float = 250.0
    ultimate_generation_events: tuple[UltimateGenerationEvent, ...] = ()
    max_magicka: float | None = None
    crowd_control_immunity_active: bool = True
    negative_effect_active: bool = True
    enlivening_overflow_trigger_seconds: float = 20.0
    low_health_boundary_seconds: float = 21.0
    enlivening_overflow_duration_seconds: float = 6.0

    @property
    def dominant_shared_state_compatible(self) -> bool:
        return bool(
            self.low_health_boundary
            and self.booming_voice_window
            and self.home_keeps == 6
            and self.continuous_attack_active
            and self.heavy_armor_pieces == 7
            and self.major_fortitude_active
            and self.provisioning_kind in {"food", "drink"}
        )


@dataclass(frozen=True)
class ExtremeHealthRecoveryBranchCompatibility:
    branch: ExtremeRecoverySpecialBranch
    status: ExtremeHealthRecoveryCompatibility
    reason: str


@dataclass(frozen=True)
class ExtremeHealthRecoveryChampionPointCompatibility:
    candidate: ChampionPointLoadoutCandidate
    status: ExtremeHealthRecoveryCompatibility
    reason: str
    available_ultimate_at_score: float | None = None
    ultimate_shortfall: float | None = None
    required_max_magicka: float | None = None


class ExtremeHealthRecoveryRuntimeCompatibilityService:
    """Review selected CP stars and special gear against one dominant runtime state."""

    _NUMERIC_PROOF_BRANCHES = frozenset(
        {
            "Alessian Order",
            "Willow's Path",
        }
    )
    _COMPATIBLE_RUNTIME_BRANCHES = frozenset(
        {
            "Adamant Lurker",
            "Bog Raider",
            "Eternal Vigor",
            "Lustrous Soulwell",
            "Old Growth Brewer",
            "Orgnum's Scales",
            "Prowler's Talisman",
            "Roksa the Warped",
            "Seventh Legion Brute",
            "The Troll King",
            "Xanmeer Genesis",
        }
    )

    @classmethod
    def assess(
        cls,
        branch: ExtremeRecoverySpecialBranch,
        state: ExtremeHealthRecoveryRuntimeState,
    ) -> ExtremeHealthRecoveryBranchCompatibility:
        name = branch.set_name
        if name == "Green Pact":
            if state.provisioning_kind == "food":
                return ExtremeHealthRecoveryBranchCompatibility(
                    branch,
                    ExtremeHealthRecoveryCompatibility.COMPATIBLE,
                    "Green Pact's food condition is active in the food branch.",
                )
            return ExtremeHealthRecoveryBranchCompatibility(
                branch,
                ExtremeHealthRecoveryCompatibility.ALTERNATE_PROVISIONING,
                "Green Pact requires food, so it cannot share the direct drink incumbent without rescoring provisioning.",
            )

        if name == "Apocryphal Inspiration":
            if state.major_fortitude_active:
                return ExtremeHealthRecoveryBranchCompatibility(
                    branch,
                    ExtremeHealthRecoveryCompatibility.REDUNDANT_NAMED_BUFF,
                    "Major Fortitude is already active; the named buff does not stack with itself.",
                )
            return ExtremeHealthRecoveryBranchCompatibility(
                branch,
                ExtremeHealthRecoveryCompatibility.COMPATIBLE,
                "Provides Major Fortitude when another source is absent.",
            )

        if branch.search_state_rule:
            return ExtremeHealthRecoveryBranchCompatibility(
                branch,
                ExtremeHealthRecoveryCompatibility.SEARCH_STATE_MUTATION,
                f"Requires separate search state: {branch.search_state_rule}.",
            )

        if name in cls._NUMERIC_PROOF_BRANCHES:
            return ExtremeHealthRecoveryBranchCompatibility(
                branch,
                ExtremeHealthRecoveryCompatibility.NUMERIC_EQUIPMENT_PROOF,
                "Condition is compatible, but the branch changes numeric stacking/reference math and must be scored with equipment state.",
            )

        if name in cls._COMPATIBLE_RUNTIME_BRANCHES:
            required = {
                "Adamant Lurker": state.standing_still,
                "Bog Raider": state.recent_enemy_death,
                "Eternal Vigor": state.low_health_boundary,
                "Lustrous Soulwell": state.recent_ultimate_cast,
                "Old Growth Brewer": state.in_combat,
                "Orgnum's Scales": state.low_health_boundary,
                "Seventh Legion Brute": state.resolve_cast_active,
                "The Troll King": state.low_health_boundary,
                "Xanmeer Genesis": state.recent_enemy_death,
            }.get(name, True)
            if required:
                return ExtremeHealthRecoveryBranchCompatibility(
                    branch,
                    ExtremeHealthRecoveryCompatibility.COMPATIBLE,
                    "Reviewed runtime condition can coexist with the dominant Dragonknight/shared recovery state.",
                )
            return ExtremeHealthRecoveryBranchCompatibility(
                branch,
                ExtremeHealthRecoveryCompatibility.INCOMPATIBLE,
                "Required runtime condition is absent from the reviewed dominant state.",
            )

        return ExtremeHealthRecoveryBranchCompatibility(
            branch,
            ExtremeHealthRecoveryCompatibility.NUMERIC_EQUIPMENT_PROOF,
            "Positive branch is not runtime-conflicting, but still requires explicit numeric equipment scoring.",
        )

    @staticmethod
    def _ultimate_at_score(state: ExtremeHealthRecoveryRuntimeState) -> float:
        remaining = max(
            0.0,
            float(state.starting_ultimate) - float(state.booming_voice_ultimate_spend),
        )
        generated = sum(
            float(event.amount)
            for event in state.ultimate_generation_events
            if (
                float(state.booming_voice_cast_seconds)
                < event.time_seconds
                <= float(state.score_seconds)
            )
        )
        return min(float(ULTIMATE_RULES.maximum_resource), remaining + generated)

    @classmethod
    def assess_champion_point(
        cls,
        candidate: ChampionPointLoadoutCandidate,
        state: ExtremeHealthRecoveryRuntimeState,
    ) -> ExtremeHealthRecoveryChampionPointCompatibility:
        name = candidate.name.casefold()
        if name == "rejuvenation":
            return ExtremeHealthRecoveryChampionPointCompatibility(
                candidate,
                ExtremeHealthRecoveryCompatibility.COMPATIBLE,
                "Unconditional while legally slotted.",
            )

        if name == "peace of mind":
            status = (
                ExtremeHealthRecoveryCompatibility.COMPATIBLE
                if state.crowd_control_immunity_active
                else ExtremeHealthRecoveryCompatibility.INCOMPATIBLE
            )
            return ExtremeHealthRecoveryChampionPointCompatibility(
                candidate,
                status,
                "Crowd Control Immunity is active at the scoring moment."
                if state.crowd_control_immunity_active
                else "Crowd Control Immunity is absent at the scoring moment.",
            )

        if name == "sustained by suffering":
            status = (
                ExtremeHealthRecoveryCompatibility.COMPATIBLE
                if state.negative_effect_active
                else ExtremeHealthRecoveryCompatibility.INCOMPATIBLE
            )
            return ExtremeHealthRecoveryChampionPointCompatibility(
                candidate,
                status,
                "A non-crowd-control negative effect can remain active during Crowd Control Immunity."
                if state.negative_effect_active
                else "No negative effect is active at the scoring moment.",
            )

        if name == "enlivening overflow":
            required_magicka = float(candidate.flat_ceiling) / 0.005
            if state.max_magicka is None:
                return ExtremeHealthRecoveryChampionPointCompatibility(
                    candidate,
                    ExtremeHealthRecoveryCompatibility.RUNTIME_PROOF_REQUIRED,
                    "Exact candidate Max Magicka is required to prove the stated Recovery cap.",
                    required_max_magicka=required_magicka,
                )
            timing_compatible = (
                state.enlivening_overflow_trigger_seconds
                <= state.low_health_boundary_seconds
                <= state.score_seconds
                and state.score_seconds - state.enlivening_overflow_trigger_seconds
                < state.enlivening_overflow_duration_seconds
            )
            cap_reachable = float(state.max_magicka) + 1e-9 >= required_magicka
            status = (
                ExtremeHealthRecoveryCompatibility.COMPATIBLE
                if timing_compatible and cap_reachable
                else ExtremeHealthRecoveryCompatibility.INCOMPATIBLE
            )
            reason = (
                "Self-overheal can trigger the buff before damage establishes the low-Health scoring state."
                if status is ExtremeHealthRecoveryCompatibility.COMPATIBLE
                else "The supplied Max Magicka or trigger-to-score timing cannot reach the 150 Recovery cap."
            )
            return ExtremeHealthRecoveryChampionPointCompatibility(
                candidate,
                status,
                reason,
                required_max_magicka=required_magicka,
            )

        if name == "strategic reserve":
            window_start = (
                float(state.booming_voice_cast_seconds)
                + float(state.booming_voice_delay_seconds)
            )
            window_end = window_start + float(state.booming_voice_duration_seconds)
            if not (
                state.booming_voice_window
                and window_start <= float(state.score_seconds) < window_end
            ):
                return ExtremeHealthRecoveryChampionPointCompatibility(
                    candidate,
                    ExtremeHealthRecoveryCompatibility.INCOMPATIBLE,
                    "The scoring moment is outside Booming Voice's delayed active window.",
                )
            available = cls._ultimate_at_score(state)
            shortfall = max(0.0, float(ULTIMATE_RULES.maximum_resource) - available)
            status = (
                ExtremeHealthRecoveryCompatibility.COMPATIBLE
                if math.isclose(shortfall, 0.0, abs_tol=1e-9)
                else ExtremeHealthRecoveryCompatibility.RUNTIME_PROOF_REQUIRED
            )
            return ExtremeHealthRecoveryChampionPointCompatibility(
                candidate,
                status,
                (
                    "Ultimate has returned to the 500 cap during Booming Voice's active window."
                    if status is ExtremeHealthRecoveryCompatibility.COMPATIBLE
                    else (
                        f"Modeled generation reaches {available:.3f} Ultimate during "
                        f"Booming Voice; {shortfall:.3f} more requires canonical source proof."
                    )
                ),
                available_ultimate_at_score=available,
                ultimate_shortfall=shortfall,
            )

        return ExtremeHealthRecoveryChampionPointCompatibility(
            candidate,
            ExtremeHealthRecoveryCompatibility.RUNTIME_PROOF_REQUIRED,
            "No reviewed Health Recovery runtime compatibility rule owns this CP star.",
        )

    @classmethod
    def assess_champion_points(
        cls,
        candidates: tuple[ChampionPointLoadoutCandidate, ...],
        state: ExtremeHealthRecoveryRuntimeState,
    ) -> tuple[ExtremeHealthRecoveryChampionPointCompatibility, ...]:
        return tuple(cls.assess_champion_point(candidate, state) for candidate in candidates)

    @classmethod
    def build(
        cls,
        branches: tuple[ExtremeRecoverySpecialBranch, ...],
        state: ExtremeHealthRecoveryRuntimeState,
    ) -> tuple[ExtremeHealthRecoveryBranchCompatibility, ...]:
        return tuple(cls.assess(branch, state) for branch in branches)


__all__ = [
    "ExtremeHealthRecoveryBranchCompatibility",
    "ExtremeHealthRecoveryChampionPointCompatibility",
    "ExtremeHealthRecoveryCompatibility",
    "ExtremeHealthRecoveryRuntimeCompatibilityService",
    "ExtremeHealthRecoveryRuntimeState",
]
