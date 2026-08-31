import sqlite3
from pathlib import Path

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from minmax.character_build.support_effect_resolver import equipped_gear_set_counts
from models.build_model import GearSlot, PlayerBuild


class _SkillEffects:
    def resolve(self, ability_id: int):
        if ability_id == 3:
            return (
                EffectVariant(
                    name="berserk",
                    layer=EffectLayer.CAST,
                    source="Combat Prayer",
                ),
            )
        return ()


class _Enchantments:
    def __init__(self, matches: dict[str, tuple[int, ...]] | None = None):
        self.matches = matches or {}

    def find_item_ids_by_label(self, label: str) -> tuple[int, ...]:
        return self.matches.get(label, ())


def _make_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE race (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                alliance TEXT,
                association TEXT
            );
            INSERT INTO race VALUES (3, 'Breton', 'Daggerfall Covenant', 'Human');

            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            INSERT INTO gear_set VALUES (332, 'Master Architect', 'standard', 5);

            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                skill_line TEXT,
                base_mechanic INTEGER,
                rank INTEGER,
                class_type TEXT,
                is_passive INTEGER,
                is_player INTEGER,
                is_crafted INTEGER,
                base_ability_id INTEGER,
                morph INTEGER
            );

            INSERT INTO ability VALUES
                (1, 'Budding Seeds', 'Green Balance', 0, 4, 'warden', 0, 1, 0, 1, 0),
                (2, 'Race Against Time', 'Psijic Order', 0, 4, '', 0, 1, 0, 2, 0),
                (3, 'Combat Prayer', 'Restoration Staff', 0, 4, '', 0, 1, 0, 3, 0),
                (4, 'Illustrious Healing', 'Restoration Staff', 0, 4, '', 0, 1, 0, 4, 0),
                (5, 'Energy Orb', 'Undaunted', 0, 4, '', 0, 1, 0, 5, 0),
                (6, 'Eternal Guardian', 'Animal Companions', 8, 4, 'warden', 0, 1, 0, 6, 0);
            """
        )


def _df_healer_like_build() -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        Race="Breton",
        EsoClass="Warden",
        Role="Healer",
        Mundus="The Ritual",
        AttributeMagicka=64,
        FrontBarWeapon=GearSlot(
            Set="Master Architect",
            WeaponType="Restoration Staff",
            Trait="Powered",
        ),
        Necklace=GearSlot(Set="Master Architect", Trait="Arcane"),
        Ring1=GearSlot(Set="Master Architect", Trait="Infused"),
        Ring2=GearSlot(Set="Master Architect", Trait="Infused"),
        FrontBarSkills=[
            "Budding Seeds",
            "Race Against Time",
            "Combat Prayer",
            "Illustrious Healing",
            "Energy Orb",
            "Eternal Guardian",
        ],
    )


def test_adapts_real_saved_bar_without_fillers_and_counts_active_staff_as_two(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(db_path)
    adapter = SavedBuildCharacterAdapter(
        db_path,
        skill_effect_repository=_SkillEffects(),
    )

    result = adapter.adapt(_df_healer_like_build(), character_id="magrat")

    assert result.build is not None
    assert result.unresolved == ()
    assert result.build.character_name == "Magrat"
    assert result.build.race_id == 3
    assert result.build.front_bar is not None
    assert result.build.back_bar is None
    assert [slot.skill_id for slot in result.build.front_bar.slots] == [
        "budding_seeds",
        "race_against_time",
        "combat_prayer",
        "illustrious_healing",
        "energy_orb",
        "eternal_guardian",
    ]
    assert result.build.front_bar.slots[2].effects[0].name == "berserk"
    assert result.build.validate() == ()
    assert equipped_gear_set_counts(result.build, BarId.FRONT) == {"332": 5}


def test_adapts_unique_saved_weapon_enchantment_item_id(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(db_path)
    saved = _df_healer_like_build()
    saved.FrontBarWeapon.Enchant = "Weapon Damage"

    result = SavedBuildCharacterAdapter(
        db_path,
        skill_effect_repository=_SkillEffects(),
        weapon_enchantment_repository=_Enchantments({"Weapon Damage": (12345,)}),
    ).adapt(saved)

    assert result.build is not None
    assert result.build.front_bar is not None
    assert result.build.front_bar.main_hand.enchantment_id == "weapon_damage"
    assert result.build.front_bar.main_hand.enchantment_item_id == 12345
    assert result.unresolved == ()


def test_ambiguous_saved_weapon_enchantment_is_not_guessed(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(db_path)
    saved = _df_healer_like_build()
    saved.FrontBarWeapon.Enchant = "Weapon Damage"

    result = SavedBuildCharacterAdapter(
        db_path,
        skill_effect_repository=_SkillEffects(),
        weapon_enchantment_repository=_Enchantments({"Weapon Damage": (12345, 67890)}),
    ).adapt(saved)

    assert result.build is not None
    assert result.build.front_bar is not None
    assert result.build.front_bar.main_hand.enchantment_id == "weapon_damage"
    assert result.build.front_bar.main_hand.enchantment_item_id is None
    assert any(
        "weapon enchantment label is ambiguous (2 matches): Weapon Damage" in message
        for message in result.unresolved
    )


def test_missing_saved_weapon_enchantment_is_reported(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(db_path)
    saved = _df_healer_like_build()
    saved.FrontBarWeapon.Enchant = "Unknown Enchant"

    result = SavedBuildCharacterAdapter(
        db_path,
        skill_effect_repository=_SkillEffects(),
        weapon_enchantment_repository=_Enchantments(),
    ).adapt(saved)

    assert result.build is not None
    assert result.build.front_bar is not None
    assert result.build.front_bar.main_hand.enchantment_id == "unknown_enchant"
    assert result.build.front_bar.main_hand.enchantment_item_id is None
    assert any(
        "weapon enchantment label not found in WeaponEnchantmentRepository: Unknown Enchant"
        in message
        for message in result.unresolved
    )


def test_ambiguous_legacy_two_handed_weapon_is_not_guessed(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(db_path)
    saved = _df_healer_like_build()
    saved.FrontBarWeapon = GearSlot(
        Set="Master Architect",
        WeaponType="Two-Handed",
    )

    result = SavedBuildCharacterAdapter(
        db_path,
        skill_effect_repository=_SkillEffects(),
    ).adapt(saved)

    assert result.build is not None
    assert result.build.front_bar is None
    assert any(
        "legacy weapon type is ambiguous and will not be guessed: Two-Handed"
        in message
        for message in result.unresolved
    )