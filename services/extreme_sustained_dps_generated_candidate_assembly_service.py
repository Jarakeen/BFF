from __future__ import annotations

"""Assemble one coherent generated sustained-DPS candidate from explicit axis choices.

Each frontier candidate may carry a convenience build/progression snapshot created from
its own baseline. This assembler deliberately copies only the state owned by that axis
onto the cross-axis context build so unrelated gear/class/identity state cannot be
silently overwritten by another frontier's stale baseline.
"""

from dataclasses import dataclass

from minmax.character_progression import CharacterProgression
from models.build_model import ChampionPointEntry, PlayerBuild
from services.extreme_sustained_dps_champion_point_frontier_service import (
    ExtremeSustainedDPSChampionPointCandidate,
)
from services.extreme_sustained_dps_cross_axis_context_service import (
    ExtremeSustainedDPSCrossAxisContext,
)
from services.extreme_sustained_dps_passive_rank_frontier_service import (
    ExtremeSustainedDPSPassiveRankCandidate,
)
from services.extreme_sustained_dps_potion_frontier_service import (
    ExtremeSustainedDPSPotionCandidate,
)
from services.extreme_sustained_dps_weapon_poison_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonLoadoutCandidate,
)
from services.extreme_sustained_dps_generated_weapon_poison_tier_loadout_frontier_service import (
    ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate,
)
from services.extreme_sustained_dps_skill_bar_frontier_service import (
    ExtremeSustainedDPSTwoBarSkillCandidate,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedCandidateCoordinate:
    champion_point_index: int
    potion_index: int
    passive_rank_index: int
    skill_bar_index: int
    poison_index: int = 0

    @property
    def identity(self) -> str:
        return (
            f"cp:{self.champion_point_index}|"
            f"potion:{self.potion_index}|"
            f"passive:{self.passive_rank_index}|"
            f"skills:{self.skill_bar_index}|"
            f"poison:{self.poison_index}"
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSAssembledCandidate:
    coordinate: ExtremeSustainedDPSGeneratedCandidateCoordinate
    build: PlayerBuild
    progression: CharacterProgression
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    poison_loadout: ExtremeSustainedDPSWeaponPoisonLoadoutCandidate | None = None
    poison_tier_loadout: (
        ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate | None
    ) = None

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSGeneratedCandidateAssemblyService:
    """Apply explicit refinement-axis state to one cross-axis materialized build."""

    @staticmethod
    def _nonempty(values) -> tuple[str, ...]:
        return tuple(
            str(value or "").strip()
            for value in values
            if str(value or "").strip()
        )

    @classmethod
    def assemble(
        cls,
        context: ExtremeSustainedDPSCrossAxisContext,
        *,
        champion_points: ExtremeSustainedDPSChampionPointCandidate,
        potion: ExtremeSustainedDPSPotionCandidate,
        passive_ranks: ExtremeSustainedDPSPassiveRankCandidate,
        skills: ExtremeSustainedDPSTwoBarSkillCandidate,
        poison_loadout: ExtremeSustainedDPSWeaponPoisonLoadoutCandidate | None = None,
        poison_tier_loadout: (
            ExtremeSustainedDPSGeneratedWeaponPoisonTierLoadoutCandidate | None
        ) = None,
    ) -> ExtremeSustainedDPSAssembledCandidate:
        coordinate = ExtremeSustainedDPSGeneratedCandidateCoordinate(
            champion_point_index=int(champion_points.structural_index),
            potion_index=int(potion.structural_index),
            passive_rank_index=int(passive_ranks.structural_index),
            skill_bar_index=int(skills.structural_index),
            poison_index=(
                0
                if poison_loadout is None
                else int(poison_loadout.structural_index)
            ),
        )

        unresolved = list(context.unresolved)
        build = PlayerBuild.from_dict(context.build.to_dict())

        # Champion Point owns only the selected CP bar state.
        build.ChampionPoints = [
            ChampionPointEntry.from_dict(entry.to_dict())
            for entry in champion_points.build.ChampionPoints
        ]

        # Potion frontier owns selection availability, never activation/uptime.
        build.Potion = str(potion.family.selected_label or "").strip()

        # Poison frontier owns only front/back equipped poison identity.
        if poison_loadout is not None:
            build.FrontBarPoison = str(
                poison_loadout.build.FrontBarPoison or ""
            ).strip()
            build.BackBarPoison = str(
                poison_loadout.build.BackBarPoison or ""
            ).strip()
            if context.one_bar_only and build.BackBarPoison:
                unresolved.append(
                    "One-bar gear context received non-empty generated back-bar poison"
                )

        if poison_tier_loadout is not None:
            if poison_loadout is None:
                unresolved.append(
                    "Generated poison tier loadout exists without poison formula loadout"
                )
            else:
                for bar in ("front", "back"):
                    tier_bar = getattr(poison_tier_loadout, bar)
                    selected_bar = getattr(poison_loadout, bar)
                    tier_poison_id = str(tier_bar.poison_id or "").strip()
                    selected_poison_id = str(
                        selected_bar.selected_label or ""
                    ).strip()
                    if tier_poison_id != selected_poison_id:
                        unresolved.append(
                            f"{bar} generated poison tier identity does not match "
                            "selected poison formula identity"
                        )

        # Skill frontier owns only the two six-slot skill bars.
        build.FrontBarSkills = list(skills.front.names)
        build.BackBarSkills = list(skills.back.names)

        if context.one_bar_only and cls._nonempty(build.BackBarSkills):
            unresolved.append(
                "One-bar gear context received non-empty generated back-bar skills"
            )

        # Passive frontier owns progression ranks, but must not erase explicit
        # ownership already proven by the cross-axis context.
        original_owned = {
            str(value or "").strip().casefold()
            for value in context.progression.owned_skill_lines
            if str(value or "").strip()
        }
        candidate_owned = {
            str(value or "").strip().casefold()
            for value in passive_ranks.progression.owned_skill_lines
            if str(value or "").strip()
        }
        missing_owned = sorted(original_owned - candidate_owned)
        if missing_owned:
            unresolved.append(
                "Passive-rank candidate erased explicit owned skill line(s): "
                + ", ".join(missing_owned)
            )
        progression = passive_ranks.progression

        build_errors = tuple(build.validate())
        unresolved.extend(build_errors)

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeSustainedDPSAssembledCandidate(
            coordinate=coordinate,
            build=build,
            progression=progression,
            evidence=(
                f"Generated refinement coordinate: {coordinate.identity}",
                f"Champion Points selected: {len(build.ChampionPoints)}",
                f"Potion selection: {build.Potion or '(none)'}",
                f"Front weapon poison: {build.FrontBarPoison or '(none)'}",
                f"Back weapon poison: {build.BackBarPoison or '(none)'}",
                (
                    "Poison tier loadout: "
                    + (
                        str(poison_tier_loadout.structural_index)
                        if poison_tier_loadout is not None
                        else "(not selected)"
                    )
                ),
                f"Front skill slots populated: {len(cls._nonempty(build.FrontBarSkills))}",
                f"Back skill slots populated: {len(cls._nonempty(build.BackBarSkills))}",
                f"Passive ranks carried: {len(progression.passive_ranks)}",
                "Axis candidates contribute only the state they own; gear/class/identity state remains cross-axis-context authoritative",
            ),
            unresolved=final_unresolved,
            poison_loadout=poison_loadout,
            poison_tier_loadout=poison_tier_loadout,
        )


__all__ = [
    "ExtremeSustainedDPSAssembledCandidate",
    "ExtremeSustainedDPSGeneratedCandidateAssemblyService",
    "ExtremeSustainedDPSGeneratedCandidateCoordinate",
]
