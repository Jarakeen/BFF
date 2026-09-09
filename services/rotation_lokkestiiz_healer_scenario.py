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
    selected_ultimate_semantic_id: str

    def __post_init__(self) -> None:
        ultimate = str(self.selected_ultimate_semantic_id or "").strip().casefold()
        if not ultimate:
            raise ValueError("Lokkestiiz healer scenario requires a selected Ultimate")
        object.__setattr__(self, "selected_ultimate_semantic_id", ultimate)

    @property
    def unresolved(self) -> tuple[str, ...]:
        """Return scenario-specific blockers without inventing a Light Attack count.

        The generic execution profile records the user's original request as an
        unresolved Light Attack count. For this real scenario the engine already
        owns the relevant mechanic: successful damaging Light/Heavy Attacks start
        or refresh the base-combat Ultimate-generation window. The remaining proof
        is therefore Ultimate affordability at each landing, which depends on the
        unresolved encounter clock windows and each candidate's actual attack
        schedule.
        """

        resolved: list[str] = []
        for item in self.execution.unresolved:
            if item.startswith("light-attack count required to restore the selected Ultimate"):
                resolved.append(
                    "Aggressive Horn affordability at each landing cannot be proven until "
                    "landing clock windows are canonically resolved; candidate Light/Heavy "
                    "Attacks must sustain the base-combat Ultimate-generation window before "
                    "each landing"
                )
            else:
                resolved.append(item)
        return tuple(resolved)

    @property
    def ready_for_clock_scheduling(self) -> bool:
        return not self.unresolved


def build_magrat_df_healer_lokkestiiz_scenario() -> LokkestiizHealerScenario:
    """Return the user-authored Lokkestiiz DF Healer encounter scenario.

    Lokkestiiz has three canonical Aerial Onslaught transitions at 80/50/20.
    The encounter loadout explicitly replaces Winter's Revenge with Elemental
    Blockade on the back bar. Aggressive Horn is the explicit landing Ultimate.
    The base DF Healer saved build is not mutated.
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
        selected_ultimate_semantic_id="aggressive_horn",
    )


__all__ = [
    "LokkestiizHealerScenario",
    "RotationBossSkillReplacement",
    "build_magrat_df_healer_lokkestiiz_scenario",
]
