from models.build_model import BossLoadout, BuildContextVariant, PlayerBuild
from services.build_context_variant_service import resolve_build_context


def test_legacy_bosses_loadout_inherits_blank_skill_slots_from_parent() -> None:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="Pure Den - Trash",
        EsoClass="Warden",
        Role="Healer",
        FrontBarSkills=[
            "Budding Seeds",
            "Radiating Regeneration",
            "Combat Prayer",
            "Illustrious Healing",
            "Energy Orb",
            "Eternal Guardian",
        ],
        BackBarSkills=[
            "Elemental Susceptibility",
            "Echoing Vigor",
            "Winter's Revenge",
            "Expansive Frost Cloak",
            "Overflowing Altar",
            "Aggressive Horn",
        ],
        BossLoadouts=[
            BossLoadout(
                BossName="Bosses",
                FrontBarSkills=["", "", "", "Enchanted Growth", "", ""],
                BackBarSkills=["", "", "", "", "", ""],
            )
        ],
    )

    resolved = resolve_build_context(build, boss_name="Lylanar and Turlassil")

    assert resolved.FrontBarSkills == [
        "Budding Seeds",
        "Radiating Regeneration",
        "Combat Prayer",
        "Enchanted Growth",
        "Energy Orb",
        "Eternal Guardian",
    ]
    assert resolved.BackBarSkills == build.BackBarSkills


def test_context_variants_remain_authoritative_over_legacy_boss_loadouts() -> None:
    build = PlayerBuild(
        Name="Magrat",
        BuildName="Pure Den - Trash",
        EsoClass="Warden",
        Role="Healer",
        FrontBarSkills=["Base 1", "Base 2", "Base 3", "Base 4", "Base 5", "Base Ult"],
        BossLoadouts=[
            BossLoadout(
                BossName="Bosses",
                FrontBarSkills=["Legacy", "", "", "", "", ""],
            )
        ],
        ContextVariants=[
            BuildContextVariant(
                ContextType="Boss",
                BossName="Bosses",
                FrontBarSkills=["Current", "", "", "", "", ""],
            )
        ],
    )

    resolved = resolve_build_context(build, boss_name="Reef Guardian")

    assert resolved.FrontBarSkills[0] == "Current"
    assert resolved.FrontBarSkills[1:] == build.FrontBarSkills[1:]
