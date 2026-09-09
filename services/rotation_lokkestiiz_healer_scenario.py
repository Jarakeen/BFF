from __future__ import annotations

from dataclasses import dataclass

from services.rotation_lokkestiiz_healer_execution_profile import (
    LokkestiizHealerExecutionProfile,
    build_magrat_df_healer_lokkestiiz_profile,
)


@dataclass(frozen=True)
class RotationBossSkillReplacement:
    """Explicit encounter-only saved-build slot substitution."""

    bar: str
    outgoing_semantic_id: str
    incoming_semantic_id: str

    def __post_init__(self) -> None:
        bar = str(self.bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("boss skill replacement bar must be front or back")
        outgoing = str(self.outgoing_semantic_id or "").strip().casefold()
        incoming = str(self.incoming_semantic_id or "").strip().casefold()
        if not outgoing or not incoming:
            raise ValueError("boss skill replacement requires outgoing and incoming semantic ids")
        if outgoing == incoming:
            raise ValueError("boss skill replacement must change the skill")
        object.__setattr__(self, "bar", bar)
        object.__setattr__(self, "outgoing_semantic_id", outgoing)
        object.__setattr__(self, "incoming_semantic_id", incoming)


@dataclass(frozen=True)
class LokkestiizHealerScenario:
    execution: LokkestiizHealerExecutionProfile
    skill_replacements: tuple[RotationBossSkillReplacement, ...]


def build_magrat_df_healer_lokkestiiz_scenario() -> LokkestiizHealerScenario:
    """Return the user-authored Lokkestiiz DF Healer encounter scenario.

    Lokkestiiz has three canonical Aerial Onslaught transitions at 80/50/20.
    The encounter loadout explicitly replaces Winter's Revenge with Elemental
    Blockade on the back bar. The base DF Healer saved build is not mutated.
    """

    return LokkestiizHealerScenario(
        execution=build_magrat_df_healer_lokkestiiz_profile(requested_cycles=3),
        skill_replacements=(
            RotationBossSkillReplacement(
                bar="back",
                outgoing_semantic_id="winters_revenge",
                incoming_semantic_id="elemental_blockade",
            ),
        ),
    )


__all__ = [
    "LokkestiizHealerScenario",
    "RotationBossSkillReplacement",
    "build_magrat_df_healer_lokkestiiz_scenario",
]
