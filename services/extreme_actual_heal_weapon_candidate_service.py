from __future__ import annotations

"""Generate legal active-bar weapon configurations for Extreme MOST Actual Heal.

The service enumerates the canonical 28 legal ESO bar configurations and
materializes each onto a cloned PlayerBuild. It deliberately changes weapon
configuration only; gear-set legality, traits, enchantments, and passive arithmetic
remain owned by the existing canonical evaluator and package/passive layers.
"""

from dataclasses import asdict

from minmax.build_candidate import BuildCandidate, BuildChange
from minmax.character_build.weapon_type import WeaponType
from models.build_model import GearSlot, PlayerBuild
from services.extreme_actual_heal_weapon_denominator_service import (
    ExtremeActualHealWeaponDenominatorService,
)


_SAVED_NAME_BY_WEAPON_TYPE = {
    WeaponType.SWORD: "Sword",
    WeaponType.AXE: "Axe",
    WeaponType.MACE: "Mace",
    WeaponType.DAGGER: "Dagger",
    WeaponType.SHIELD: "Shield",
    WeaponType.GREATSWORD: "Greatsword",
    WeaponType.BATTLEAXE: "Battleaxe",
    WeaponType.MAUL: "Maul",
    WeaponType.BOW: "Bow",
    WeaponType.RESTORATION_STAFF: "Restoration Staff",
    WeaponType.FROST_STAFF: "Ice Staff",
    WeaponType.FLAME_STAFF: "Inferno Staff",
    WeaponType.LIGHTNING_STAFF: "Lightning Staff",
}


class ExtremeActualHealWeaponCandidateService:
    """Materialize every legal active-bar weapon shape for H1 rescoring."""

    @staticmethod
    def _slot_copy(source: GearSlot, weapon_type: WeaponType) -> GearSlot:
        slot = GearSlot.from_dict(source.to_dict())
        slot.WeaponType = _SAVED_NAME_BY_WEAPON_TYPE[weapon_type]
        return slot

    @staticmethod
    def _empty_offhand() -> GearSlot:
        return GearSlot()

    @staticmethod
    def _config_payload(main: GearSlot, offhand: GearSlot) -> dict[str, object]:
        return {
            "main": main.to_dict(),
            "offhand": offhand.to_dict(),
        }

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
        active_bar: str = "front",
    ) -> tuple[BuildCandidate, ...]:
        bar = "back" if str(active_bar or "front").casefold() == "back" else "front"
        main_field = "BackBarWeapon" if bar == "back" else "FrontBarWeapon"
        off_field = "BackBarOffHand" if bar == "back" else "FrontBarOffHand"
        baseline_main = getattr(baseline_build, main_field)
        baseline_off = getattr(baseline_build, off_field)
        before = self._config_payload(baseline_main, baseline_off)

        result: list[BuildCandidate] = []
        for config in ExtremeActualHealWeaponDenominatorService.legal_bar_configurations():
            build = PlayerBuild.from_dict(baseline_build.to_dict())

            # Preserve all non-identity metadata on an existing slot so quality,
            # level, trait, enchant, and set state remain visible to canonical
            # legality/math. Two-slot weapons explicitly clear the off-hand.
            main = self._slot_copy(getattr(build, main_field), config.main_hand)
            if config.off_hand is WeaponType.NONE:
                offhand = self._empty_offhand()
            else:
                source_offhand = getattr(build, off_field)
                if source_offhand.is_empty:
                    source_offhand = GearSlot(
                        Quality=main.Quality,
                        Level=main.Level,
                    )
                offhand = self._slot_copy(source_offhand, config.off_hand)

            setattr(build, main_field, main)
            setattr(build, off_field, offhand)
            after = self._config_payload(main, offhand)
            if after == before:
                continue

            token = f"{config.main_hand.value}+{config.off_hand.value}"
            result.append(
                BuildCandidate.from_build(
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    candidate_id=f"{baseline_build_id}:weapon-config:{bar}:{token}",
                    candidate_build=build,
                    changes=(
                        BuildChange.from_values(
                            path=f"{bar.title()}BarWeaponConfiguration",
                            before=before,
                            after=after,
                            source="extreme:actual-heal:weapon-configuration",
                        ),
                    ),
                    candidate_source="extreme:actual-heal:weapon-configuration",
                )
            )

        return tuple(result)


__all__ = ["ExtremeActualHealWeaponCandidateService"]
