from __future__ import annotations

"""Compose cross-axis legality context for one generated sustained-DPS candidate.

This service does not score DPS and does not invent progression ownership. It binds
already-materialized build/progression/gear facts into one coherent legality record:
class-route lines, explicit shared-line ownership, equipped weapon lines, equipped
armor lines, transformation state, scribed identities, and bar-access rules.
"""

from dataclasses import dataclass
from dataclasses import replace

from minmax.character_build.weapon_type import WeaponType, resolve_weapon_skill_line
from minmax.character_progression import CharacterProgression
from minmax.eso_weapon_type_id import weapon_type_from_saved_name
from models.build_model import PlayerBuild
from services.extreme_dual_bar_gear_state_service import (
    ExtremeDualBarGearState,
    ExtremeDualBarGearStateService,
)
from services.extreme_gear_bar_access_service import (
    ExtremeGearBarAccess,
    ExtremeGearBarAccessService,
)
from services.extreme_sustained_dps_skill_bar_frontier_service import (
    ExtremeSustainedDPSSkillBarLegalityContext,
)
from services.skill_bar_eligibility import CLASS_SKILL_LINES


_ARMOR_WEIGHT_TO_LINE = {
    "light": "Light Armor",
    "medium": "Medium Armor",
    "heavy": "Heavy Armor",
}


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _line_key(value: object) -> str:
    return " ".join(
        _clean(value).casefold().replace("_", " ").replace("-", " ").split()
    )


@dataclass(frozen=True)
class ExtremeSustainedDPSCrossAxisContext:
    build: PlayerBuild
    progression: CharacterProgression
    front_skill_context: ExtremeSustainedDPSSkillBarLegalityContext
    back_skill_context: ExtremeSustainedDPSSkillBarLegalityContext
    bar_access: ExtremeGearBarAccess
    class_skill_lines: tuple[str, ...]
    equipped_armor_lines: tuple[str, ...]
    front_weapon_lines: tuple[str, ...]
    back_weapon_lines: tuple[str, ...]
    explicit_owned_skill_lines: tuple[str, ...]
    one_bar_only: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSCrossAxisContextService:
    """Bind generated structural/equipment/progression facts into skill legality."""

    @staticmethod
    def _class_lines(build: PlayerBuild) -> tuple[str, ...]:
        explicit = tuple(
            _clean(value)
            for value in tuple(getattr(build, "ClassSkillLines", ()) or ())
            if _clean(value)
        )
        if explicit:
            return tuple(dict.fromkeys(explicit))

        selected = _line_key(getattr(build, "EsoClass", ""))
        native = CLASS_SKILL_LINES.get(selected, frozenset())
        return tuple(sorted(native, key=str.casefold))

    @staticmethod
    def _armor_lines(build: PlayerBuild) -> tuple[str, ...]:
        values: set[str] = set()
        for entry in build.Armor.values():
            weight = _clean(entry.get("Weight", "")).casefold()
            line = _ARMOR_WEIGHT_TO_LINE.get(weight)
            if line:
                values.add(line)
        return tuple(sorted(values, key=str.casefold))

    @staticmethod
    def _weapon_line(
        build: PlayerBuild,
        active_bar: str,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        main, offhand = build.active_weapon_slots(active_bar)
        main_raw = _clean(main.WeaponType)
        offhand_raw = _clean(offhand.WeaponType)

        if not main_raw:
            return (), (f"{active_bar}: main weapon type is empty",)

        main_type = weapon_type_from_saved_name(main_raw)
        if main_type is None:
            return (), (f"{active_bar}: weapon type is unresolved: {main_raw}",)

        offhand_type = WeaponType.NONE
        if offhand_raw:
            resolved_offhand = weapon_type_from_saved_name(offhand_raw)
            if resolved_offhand is None:
                return (), (f"{active_bar}: off-hand weapon type is unresolved: {offhand_raw}",)
            offhand_type = resolved_offhand

        try:
            line = resolve_weapon_skill_line(main_type, offhand_type).value
        except ValueError as exc:
            return (), (f"{active_bar}: weapon-skill-line legality unresolved: {exc}",)

        display = " ".join(part.capitalize() for part in line.replace("_", " ").split())
        if line == "one_hand_and_shield":
            display = "One Hand and Shield"
        elif line == "two_handed":
            display = "Two Handed"
        elif line == "dual_wield":
            display = "Dual Wield"
        elif line == "destruction_staff":
            display = "Destruction Staff"
        elif line == "restoration_staff":
            display = "Restoration Staff"
        return (display,), ()

    @staticmethod
    def _scribed_ids(build: PlayerBuild) -> tuple[tuple[int, ...], tuple[str, ...]]:
        recipes = tuple(getattr(build, "ScribedSkillRecipes", ()) or ())
        if not recipes:
            return (), ()
        return (), (
            "Configured scribed skill recipes have no canonical ability-ID mapping in PlayerBuild; "
            "generated scribed-skill legality remains unresolved",
        )

    @classmethod
    def compose(
        cls,
        build: PlayerBuild,
        progression: CharacterProgression,
        *,
        gear_state: ExtremeDualBarGearState,
    ) -> ExtremeSustainedDPSCrossAxisContext:
        unresolved: list[str] = []
        gear_problems = ExtremeDualBarGearStateService.validate(gear_state)
        unresolved.extend(gear_problems)

        try:
            candidate = ExtremeDualBarGearStateService.materialize(build, gear_state)
        except ValueError as exc:
            candidate = PlayerBuild.from_dict(build.to_dict())
            unresolved.append(str(exc))

        bar_access = ExtremeGearBarAccessService.resolve(gear_state)
        unresolved.extend(bar_access.unresolved)

        class_lines = cls._class_lines(candidate)
        if not class_lines:
            unresolved.append("Candidate class-route skill lines are unavailable")

        armor_lines = cls._armor_lines(candidate)
        front_weapon, front_unresolved = cls._weapon_line(candidate, "front")
        unresolved.extend(front_unresolved)

        if bar_access.allows("back"):
            back_weapon, back_unresolved = cls._weapon_line(candidate, "back")
            unresolved.extend(back_unresolved)
        else:
            back_weapon = ()

        owned = tuple(
            dict.fromkeys(
                _clean(value)
                for value in progression.owned_skill_lines
                if _clean(value)
            )
        )
        scribed, scribed_unresolved = cls._scribed_ids(candidate)
        unresolved.extend(scribed_unresolved)
        transformed = _clean(candidate.TransformedForm).casefold() or None

        front_context = ExtremeSustainedDPSSkillBarLegalityContext(
            character_class=_clean(candidate.EsoClass),
            class_skill_lines=class_lines,
            owned_skill_lines=owned,
            weapon_skill_lines=front_weapon,
            armor_skill_lines=armor_lines,
            vampire=bool(candidate.Vampire),
            werewolf=bool(candidate.Werewolf),
            transformed_form=transformed,
            allowed_scribed_ability_ids=scribed,
        )
        back_context = ExtremeSustainedDPSSkillBarLegalityContext(
            character_class=_clean(candidate.EsoClass),
            class_skill_lines=class_lines,
            owned_skill_lines=owned,
            weapon_skill_lines=back_weapon,
            armor_skill_lines=armor_lines,
            vampire=bool(candidate.Vampire),
            werewolf=bool(candidate.Werewolf),
            transformed_form=transformed,
            allowed_scribed_ability_ids=scribed,
        )

        # Class-route identity belongs to build state, not character-owned shared
        # progression. Preserve that boundary while exposing the selected route.
        candidate.ClassSkillLines = list(class_lines)

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        return ExtremeSustainedDPSCrossAxisContext(
            build=candidate,
            progression=progression,
            front_skill_context=front_context,
            back_skill_context=back_context,
            bar_access=bar_access,
            class_skill_lines=class_lines,
            equipped_armor_lines=armor_lines,
            front_weapon_lines=front_weapon,
            back_weapon_lines=back_weapon,
            explicit_owned_skill_lines=owned,
            one_bar_only=not bool(bar_access.can_swap),
            evidence=(
                f"Candidate class-route lines: {len(class_lines)}",
                f"Explicit shared owned skill lines: {len(owned)}",
                f"Equipped armor skill lines: {len(armor_lines)}",
                f"Front weapon skill lines: {len(front_weapon)}",
                f"Back weapon skill lines: {len(back_weapon)}",
                f"Activatable bars: {', '.join(bar_access.activatable_bars) or '(none)'}",
                "Class-route, explicit ownership, equipped weapon/armor evidence, and bar access remain distinct legality facts",
            ),
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSCrossAxisContext",
    "ExtremeSustainedDPSCrossAxisContextService",
]
