from __future__ import annotations

from models.build_model import BuildContextVariant, GearSlot, PlayerBuild
from services.build_context_variant_service import resolve_build_context, select_context_variant


def test_context_variants_round_trip_with_full_override_shape() -> None:
    build = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="Healer Base",
        ContextVariants=[
            BuildContextVariant(
                ContextType="Team",
                TeamName="Swine & Punishment",
                Mundus="The Atronach",
                Armor={"Head": {"Set": "Pearls of Ehlnofey", "Trait": "Divines"}},
                FrontBarWeapon=GearSlot(Set="Roaring Opportunist", Trait="Powered"),
                FrontBarSkills=["Combat Prayer", "", "", "", "", ""],
                Food="Clockwork Citrus Filet",
            )
        ],
    )

    restored = PlayerBuild.from_dict(build.to_dict())
    assert len(restored.ContextVariants) == 1
    variant = restored.ContextVariants[0]
    assert variant.TeamName == "Swine & Punishment"
    assert variant.Armor["Head"]["Set"] == "Pearls of Ehlnofey"
    assert variant.FrontBarWeapon.Set == "Roaring Opportunist"


def test_legacy_boss_loadouts_migrate_in_memory_to_boss_variants() -> None:
    restored = PlayerBuild.from_dict(
        {
            "Name": "Magrat",
            "BossLoadouts": [
                {
                    "BossName": "Xalvakka",
                    "FrontBarSkills": ["Combat Prayer", "", "", "", "", ""],
                    "Food": "Ghastly Eye Bowl",
                }
            ],
        }
    )

    assert restored.BossLoadouts[0].BossName == "Xalvakka"
    assert restored.ContextVariants[0].ContextType == "Boss"
    assert restored.ContextVariants[0].BossName == "Xalvakka"


def test_team_boss_variant_precedence_is_team_boss_then_team_then_boss() -> None:
    build = PlayerBuild(
        Name="Magrat",
        Mundus="The Ritual",
        FrontBarSkills=["Base 1", "Base 2", "Base 3", "Base 4", "Base 5", "Base Ult"],
        ContextVariants=[
            BuildContextVariant(ContextType="Boss", BossName="Boss A", Mundus="The Thief"),
            BuildContextVariant(ContextType="Team", TeamName="SW", Mundus="The Atronach"),
            BuildContextVariant(
                ContextType="Team + Boss",
                TeamName="SW",
                BossName="Boss A",
                Mundus="The Shadow",
                FrontBarSkills=["Override 1", "", "", "", "", ""],
            ),
        ],
    )

    assert select_context_variant(build, team_name="SW", boss_name="Boss A").Mundus == "The Shadow"
    assert resolve_build_context(build, team_name="SW", boss_name="Boss A").Mundus == "The Shadow"
    assert resolve_build_context(build, team_name="SW", boss_name="Other").Mundus == "The Atronach"
    assert resolve_build_context(build, team_name="Other", boss_name="Boss A").Mundus == "The Thief"


def test_sparse_variant_inherits_unchanged_base_fields() -> None:
    build = PlayerBuild(
        Name="Magrat",
        Mundus="The Ritual",
        Armor={"Head": {"Set": "Spell Power Cure", "Trait": "Divines"}},
        FrontBarWeapon=GearSlot(Set="Master Architect", Trait="Powered"),
        FrontBarSkills=["Base 1", "Base 2", "Base 3", "Base 4", "Base 5", "Base Ult"],
        Food="Base Food",
        ContextVariants=[
            BuildContextVariant(
                ContextType="Team",
                TeamName="SW",
                Armor={"Head": {"Set": "Pearls of Ehlnofey"}},
                FrontBarSkills=["SW 1", "", "", "", "", ""],
            )
        ],
    )

    resolved = resolve_build_context(build, team_name="SW")
    assert resolved.Armor["Head"]["Set"] == "Pearls of Ehlnofey"
    assert resolved.Armor["Head"]["Trait"] == "Divines"
    assert resolved.FrontBarWeapon.Set == "Master Architect"
    assert resolved.FrontBarSkills == ["SW 1", "Base 2", "Base 3", "Base 4", "Base 5", "Base Ult"]
    assert resolved.Food == "Base Food"
