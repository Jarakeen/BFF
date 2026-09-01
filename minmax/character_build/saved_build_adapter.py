from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from models.build_model import GearSlot as LegacyGearSlot, PlayerBuild
from services.skill_bar_eligibility import is_eligible

from ..champion_point_effect_variant_resolver import ChampionPointEffectVariantResolver
from ..gear_set_category_resolver import GearSetCategoryResolver
from ..gear_set_repository import GearSetRepository
from ..race_repository import RaceRepository
from ..role import Role
from ..skill_effect_repository import SkillEffectRepository
from ..weapon_enchantment_repository import WeaponEnchantmentRepository
from .bar import Bar
from .champion_points import ChampionPointAllocation
from .character_build import CharacterBuild
from .character_class import CharacterClass
from .effect_layer import BarId
from .gear_piece import ArmorPiece, GearPieceCategory, GearSlot
from .slotted_skill import SlottedSkill
from .weapon import Weapon
from .weapon_type import WeaponType


@dataclass(frozen=True)
class SavedBuildAdaptation:
    """Result of converting one legacy PlayerBuild into canonical mechanics."""

    build: CharacterBuild | None
    unresolved: tuple[str, ...] = ()


_CLASS_BY_NAME = {
    "dragonknight": CharacterClass.DRAGONKNIGHT,
    "sorcerer": CharacterClass.SORCERER,
    "nightblade": CharacterClass.NIGHTBLADE,
    "templar": CharacterClass.TEMPLAR,
    "warden": CharacterClass.WARDEN,
    "necromancer": CharacterClass.NECROMANCER,
    "arcanist": CharacterClass.ARCANIST,
}

_ROLE_BY_NAME = {
    "tank": Role.TANK,
    "healer": Role.HEALER,
    "heal": Role.HEALER,
    "dd": Role.DD,
    "dps": Role.DD,
    "damage dealer": Role.DD,
}

_WEAPON_TYPE_BY_NAME = {
    "bow": WeaponType.BOW,
    "inferno staff": WeaponType.FLAME_STAFF,
    "fire staff": WeaponType.FLAME_STAFF,
    "flame staff": WeaponType.FLAME_STAFF,
    "lightning staff": WeaponType.LIGHTNING_STAFF,
    "shock staff": WeaponType.LIGHTNING_STAFF,
    "ice staff": WeaponType.FROST_STAFF,
    "frost staff": WeaponType.FROST_STAFF,
    "restoration staff": WeaponType.RESTORATION_STAFF,
    "sword": WeaponType.SWORD,
    "axe": WeaponType.AXE,
    "mace": WeaponType.MACE,
    "dagger": WeaponType.DAGGER,
    "shield": WeaponType.SHIELD,
}

_AMBIGUOUS_WEAPON_TYPES = frozenset(
    {
        "two handed",
        "two-handed",
        "dual wield",
        "one hand and shield",
    }
)

_GEAR_SLOT_BY_LEGACY_NAME = {
    "Head": GearSlot.HEAD,
    "Shoulders": GearSlot.SHOULDERS,
    "Chest": GearSlot.CHEST,
    "Hands": GearSlot.HANDS,
    "Waist": GearSlot.WAIST,
    "Legs": GearSlot.LEGS,
    "Feet": GearSlot.FEET,
    "Necklace": GearSlot.NECKLACE,
    "Ring1": GearSlot.RING_1,
    "Ring2": GearSlot.RING_2,
}


def _text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _text(value).casefold()


def _canonical_skill_line(value: object) -> str:
    text = _key(value).replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def _stable_skill_id(value: object) -> str:
    text = _key(value).replace("'", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _parse_level(value: object) -> int | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"\d+", text)
    if match is None:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


class SavedBuildCharacterAdapter:
    """Convert the Builds UI PlayerBuild model into canonical CharacterBuild.

    The adapter resolves only identities that existing repositories can prove.
    Unknown sets, races, abilities, enchantments, or ambiguous legacy weapon
    aggregates are returned as unresolved diagnostics instead of guessed.

    Static character-sheet effects such as armor glyph magnitude, food stats,
    Mundus magnitude, and Champion Point math remain owned by the existing
    BuildCalculationContext pipeline. This adapter's job is canonical build
    structure and EffectVariant-capable sources, not a parallel stat engine.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        race_repository: RaceRepository | None = None,
        gear_set_repository: GearSetRepository | None = None,
        gear_set_category_resolver: GearSetCategoryResolver | None = None,
        skill_effect_repository: SkillEffectRepository | None = None,
        weapon_enchantment_repository: WeaponEnchantmentRepository | None = None,
        champion_point_effect_resolver: ChampionPointEffectVariantResolver | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.race_repository = race_repository or RaceRepository(self.database_path)
        self.gear_set_repository = gear_set_repository or GearSetRepository(
            self.database_path
        )
        self.gear_set_category_resolver = (
            gear_set_category_resolver or GearSetCategoryResolver(self.database_path)
        )
        self.skill_effect_repository = (
            skill_effect_repository or SkillEffectRepository(self.database_path)
        )
        self.weapon_enchantment_repository = (
            weapon_enchantment_repository
            or WeaponEnchantmentRepository(self.database_path)
        )
        self.champion_point_effect_resolver = (
            champion_point_effect_resolver
            or ChampionPointEffectVariantResolver(self.database_path)
        )

    def adapt(
        self,
        saved: PlayerBuild,
        *,
        character_id: str | None = None,
    ) -> SavedBuildAdaptation:
        unresolved: list[str] = []

        character_class = _CLASS_BY_NAME.get(_key(saved.EsoClass))
        if character_class is None:
            unresolved.append(
                f"Unsupported or missing ESO class: {saved.EsoClass or '(empty)'}"
            )

        role = _ROLE_BY_NAME.get(_key(saved.Role))
        if role is None:
            unresolved.append(
                f"Unsupported or missing role: {saved.Role or '(empty)'}"
            )

        if character_class is None or role is None:
            return SavedBuildAdaptation(None, tuple(unresolved))

        race_id: int | None = None
        if _text(saved.Race):
            race = self.race_repository.get_race(_text(saved.Race))
            if race is None:
                unresolved.append(f"Race not found in RaceRepository: {saved.Race}")
            else:
                race_id = int(race.id)

        armor, mythic, gear_unresolved = self._adapt_non_weapon_gear(saved)
        unresolved.extend(gear_unresolved)

        champion_points, cp_unresolved = self._adapt_champion_points(saved)
        unresolved.extend(cp_unresolved)

        front_bar, front_unresolved = self._adapt_bar(
            saved,
            BarId.FRONT,
            character_class,
        )
        back_bar, back_unresolved = self._adapt_bar(
            saved,
            BarId.BACK,
            character_class,
        )
        unresolved.extend(front_unresolved)
        unresolved.extend(back_unresolved)

        canonical = CharacterBuild(
            name=_text(saved.BuildName) or _text(saved.Name) or "Saved Build",
            character_class=character_class,
            role=role,
            race_id=race_id,
            character_id=character_id,
            character_name=_text(saved.Name) or None,
            vampire=bool(saved.Vampire),
            werewolf=bool(saved.Werewolf),
            mundus_id=_text(saved.Mundus) or None,
            food_id=_text(saved.Food) or None,
            potion_id=_text(saved.Potion) or None,
            mythic=mythic,
            armor=armor,
            champion_points=champion_points,
            front_bar=front_bar,
            back_bar=back_bar,
        )

        for problem in canonical.validate():
            unresolved.append(f"Canonical build validation: {problem}")

        return SavedBuildAdaptation(canonical, tuple(dict.fromkeys(unresolved)))

    def _adapt_champion_points(
        self,
        saved: PlayerBuild,
    ) -> tuple[tuple[ChampionPointAllocation, ...], tuple[str, ...]]:
        """Preserve saved CP allocations and attach only verified dynamic effects."""
        allocations: list[ChampionPointAllocation] = []
        unresolved: list[str] = []

        for index, entry in enumerate(saved.ChampionPoints, start=1):
            name = _text(entry.Name)
            if not name:
                continue

            points_text = _text(entry.Points)
            try:
                points = int(points_text or "0")
            except (TypeError, ValueError):
                unresolved.append(
                    f"Champion Point entry {index} has invalid allocation: {name}: {entry.Points}"
                )
                continue

            if points < 0:
                unresolved.append(
                    f"Champion Point entry {index} has negative allocation: {name}: {points}"
                )
                continue

            effects, effect_unresolved = self.champion_point_effect_resolver.resolve(
                name,
                points,
            )
            unresolved.extend(effect_unresolved)

            allocations.append(
                ChampionPointAllocation(
                    node_id=_stable_skill_id(name),
                    points=points,
                    effects=effects,
                )
            )

        return tuple(allocations), tuple(unresolved)

    def _adapt_non_weapon_gear(
        self,
        saved: PlayerBuild,
    ) -> tuple[tuple[ArmorPiece, ...], ArmorPiece | None, tuple[str, ...]]:
        unresolved: list[str] = []
        pieces: list[ArmorPiece] = []
        mythics: list[ArmorPiece] = []

        entries: list[tuple[str, object]] = list(saved.Armor.items())
        entries.extend(
            [
                ("Necklace", saved.Necklace),
                ("Ring1", saved.Ring1),
                ("Ring2", saved.Ring2),
            ]
        )

        for legacy_slot, entry in entries:
            slot = _GEAR_SLOT_BY_LEGACY_NAME.get(legacy_slot)
            if slot is None:
                unresolved.append(f"Unknown legacy gear slot: {legacy_slot}")
                continue

            set_name = self._entry_value(entry, "Set")
            second_set = self._entry_value(entry, "Set2")
            trait = self._entry_value(entry, "Trait")
            quality = self._entry_value(entry, "Quality")
            weight = self._entry_value(entry, "Weight")
            level = _parse_level(self._entry_value(entry, "Level"))

            if not any((set_name, second_set, trait, quality, weight, level)):
                continue

            if second_set:
                unresolved.append(
                    f"{legacy_slot}: secondary set field is not canonicalized yet: {second_set}"
                )

            set_id: str | None = None
            category = GearPieceCategory.NORMAL
            if set_name:
                gear_set = self.gear_set_repository.get_set(set_name)
                if gear_set is None:
                    unresolved.append(
                        f"{legacy_slot}: gear set not found in GearSetRepository: {set_name}"
                    )
                else:
                    set_id = str(gear_set.id)
                    category = self.gear_set_category_resolver.resolve(
                        int(gear_set.id),
                        raw_category=gear_set.category,
                    )

            piece = ArmorPiece(
                slot=slot,
                category=category,
                set_id=set_id,
                trait=trait or None,
                quality=quality or None,
                level=level,
                weight=weight or None,
            )
            if category == GearPieceCategory.MYTHIC:
                mythics.append(piece)
            else:
                pieces.append(piece)

        mythic: ArmorPiece | None = None
        if len(mythics) == 1:
            mythic = mythics[0]
        elif len(mythics) > 1:
            unresolved.append(
                f"Saved build contains {len(mythics)} mythics; ESO allows at most one."
            )
            pieces.extend(mythics)

        return tuple(pieces), mythic, tuple(unresolved)

    def _adapt_bar(
        self,
        saved: PlayerBuild,
        bar_id: BarId,
        character_class: CharacterClass,
    ) -> tuple[Bar | None, tuple[str, ...]]:
        unresolved: list[str] = []
        if bar_id == BarId.FRONT:
            main_entry = saved.FrontBarWeapon
            off_entry = saved.FrontBarOffHand
            names = tuple(saved.FrontBarSkills)
        else:
            main_entry = saved.BackBarWeapon
            off_entry = saved.BackBarOffHand
            names = tuple(saved.BackBarSkills)

        bar_has_data = (
            not main_entry.is_empty
            or not off_entry.is_empty
            or any(_text(name) for name in names)
        )
        if not bar_has_data:
            return None, ()

        main_hand, main_unresolved = self._adapt_weapon(
            main_entry,
            f"{bar_id.value} main hand",
        )
        off_hand, off_unresolved = self._adapt_weapon(
            off_entry,
            f"{bar_id.value} off hand",
            optional=True,
        )
        unresolved.extend(main_unresolved)
        unresolved.extend(off_unresolved)

        if len(names) != 6 or any(not _text(name) for name in names):
            unresolved.append(
                f"{bar_id.value} bar is incomplete; six named saved skill slots are required for canonical adaptation."
            )
            return None, tuple(unresolved)

        slots: list[SlottedSkill] = []
        for index, name in enumerate(names):
            record = self._ability_record(_text(name))
            if record is None:
                unresolved.append(
                    f"{bar_id.value} slot {index + 1}: ability not found by exact name: {name}"
                )
                continue

            ability_id, canonical_name, skill_line, base_mechanic, eligibility = record
            if not is_eligible(
                eligibility,
                character_class=character_class.value,
                slot_index=index,
                vampire=saved.Vampire,
                werewolf=saved.Werewolf,
            ):
                unresolved.append(
                    f"{bar_id.value} slot {index + 1}: {canonical_name} is not eligible for this saved build."
                )
                continue

            slots.append(
                SlottedSkill(
                    skill_id=_stable_skill_id(canonical_name),
                    skill_line_id=_canonical_skill_line(skill_line),
                    is_ultimate=(int(base_mechanic or 0) == 8),
                    is_cast=True,
                    requires_active_bar=True,
                    effects=tuple(self.skill_effect_repository.resolve(ability_id)),
                )
            )

        if len(slots) != 6 or main_hand is None:
            return None, tuple(unresolved)

        return (
            Bar(
                bar_id=bar_id,
                main_hand=main_hand,
                off_hand=off_hand,
                slots=tuple(slots),
            ),
            tuple(unresolved),
        )

    def _adapt_weapon(
        self,
        entry: LegacyGearSlot,
        label: str,
        *,
        optional: bool = False,
    ) -> tuple[Weapon | None, tuple[str, ...]]:
        if entry.is_empty:
            return None, () if optional else (f"{label}: no weapon selected.",)

        unresolved: list[str] = []
        weapon_name = _key(entry.WeaponType)
        if weapon_name in _AMBIGUOUS_WEAPON_TYPES:
            unresolved.append(
                f"{label}: legacy weapon type is ambiguous and will not be guessed: {entry.WeaponType}"
            )
            return None, tuple(unresolved)

        weapon_type = _WEAPON_TYPE_BY_NAME.get(weapon_name)
        if weapon_type is None:
            unresolved.append(
                f"{label}: unsupported or missing weapon type: {entry.WeaponType or '(empty)'}"
            )
            return None, tuple(unresolved)

        set_id: str | None = None
        if _text(entry.Set):
            gear_set = self.gear_set_repository.get_set(_text(entry.Set))
            if gear_set is None:
                unresolved.append(
                    f"{label}: gear set not found in GearSetRepository: {entry.Set}"
                )
            else:
                set_id = str(gear_set.id)

        if _text(entry.Set2):
            unresolved.append(
                f"{label}: secondary set field is not canonicalized yet: {entry.Set2}"
            )

        enchantment_item_id: int | None = None
        enchantment_label = _text(entry.Enchant)
        if enchantment_label:
            matches = self.weapon_enchantment_repository.find_item_ids_by_label(
                enchantment_label
            )
            if len(matches) == 1:
                enchantment_item_id = matches[0]
            elif not matches:
                unresolved.append(
                    f"{label}: weapon enchantment label not found in WeaponEnchantmentRepository: {enchantment_label}"
                )
            else:
                unresolved.append(
                    f"{label}: weapon enchantment label is ambiguous ({len(matches)} matches): {enchantment_label}"
                )

        return (
            Weapon(
                weapon_type=weapon_type,
                trait=_text(entry.Trait) or None,
                enchantment_item_id=enchantment_item_id,
                set_id=set_id,
                quality=_text(entry.Quality) or None,
            ),
            tuple(unresolved),
        )

    def _ability_record(
        self,
        name: str,
    ) -> tuple[int, str, str, int, dict] | None:
        if not self.database_path.exists():
            return None

        with sqlite3.connect(self.database_path) as db:
            columns = {
                str(row[1])
                for row in db.execute("PRAGMA table_info(ability)").fetchall()
            }
            required = {"ability_id", "name", "skill_line"}
            if not required.issubset(columns):
                return None

            optional = {
                "base_mechanic": "0",
                "rank": "0",
                "class_type": "''",
                "is_passive": "0",
                "is_player": "1",
                "is_crafted": "0",
                "base_ability_id": "ability_id",
                "morph": "0",
            }
            selected = ["ability_id", "name", "skill_line"]
            selected.extend(
                column if column in columns else f"{default} AS {column}"
                for column, default in optional.items()
            )
            order = "COALESCE(rank, 0) DESC, ability_id DESC" if "rank" in columns else "ability_id DESC"
            row = db.execute(
                f"""
                SELECT {', '.join(selected)}
                FROM ability
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                ORDER BY {order}
                LIMIT 1
                """,
                (name,),
            ).fetchone()

        if row is None:
            return None

        (
            ability_id,
            canonical_name,
            skill_line,
            base_mechanic,
            rank,
            class_type,
            is_passive,
            is_player,
            is_crafted,
            base_ability_id,
            morph,
        ) = row
        eligibility = {
            "ability_id": ability_id,
            "name": canonical_name,
            "skill_line": skill_line,
            "base_mechanic": base_mechanic,
            "rank": rank,
            "class_type": class_type,
            "is_passive": is_passive,
            "is_player": is_player,
            "is_crafted": is_crafted,
            "base_ability_id": base_ability_id,
            "morph": morph,
        }
        return (
            int(ability_id),
            str(canonical_name),
            str(skill_line or ""),
            int(base_mechanic or 0),
            eligibility,
        )

    @staticmethod
    def _entry_value(entry: object, field: str) -> str:
        if isinstance(entry, dict):
            return _text(entry.get(field, ""))
        return _text(getattr(entry, field, ""))
