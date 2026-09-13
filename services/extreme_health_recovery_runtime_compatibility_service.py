from __future__ import annotations

"""Runtime compatibility facts for the proven Extreme Health Recovery route.

This layer does not score the final record. It records whether already-reviewed
conditions can coexist in one legal scoring moment and identifies branches that
require an alternate provisioning/search state rather than silently stacking every
independent component maximum.
"""

from dataclasses import dataclass
from enum import Enum

from services.extreme_gear_set_recovery_special_branch_service import (
    ExtremeRecoverySpecialBranch,
)


class ExtremeHealthRecoveryCompatibility(str, Enum):
    COMPATIBLE = "compatible"
    ALTERNATE_PROVISIONING = "alternate_provisioning"
    REDUNDANT_NAMED_BUFF = "redundant_named_buff"
    SEARCH_STATE_MUTATION = "search_state_mutation"
    NUMERIC_EQUIPMENT_PROOF = "numeric_equipment_proof"
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


class ExtremeHealthRecoveryRuntimeCompatibilityService:
    """Review special gear branches against the dominant shared runtime state."""

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

    @classmethod
    def build(
        cls,
        branches: tuple[ExtremeRecoverySpecialBranch, ...],
        state: ExtremeHealthRecoveryRuntimeState,
    ) -> tuple[ExtremeHealthRecoveryBranchCompatibility, ...]:
        return tuple(cls.assess(branch, state) for branch in branches)


__all__ = [
    "ExtremeHealthRecoveryBranchCompatibility",
    "ExtremeHealthRecoveryCompatibility",
    "ExtremeHealthRecoveryRuntimeCompatibilityService",
    "ExtremeHealthRecoveryRuntimeState",
]
