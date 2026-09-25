from __future__ import annotations

from minmax.character_progression import CharacterProgression
from models.build_model import ChampionPointEntry, PlayerBuild
from services.extreme_sustained_dps_champion_point_frontier_service import (
    ExtremeSustainedDPSChampionPointCandidate,
)
from services.extreme_sustained_dps_cross_axis_context_service import (
    ExtremeSustainedDPSCrossAxisContext,
)
from services.extreme_sustained_dps_generated_candidate_assembly_service import (
    ExtremeSustainedDPSGeneratedCandidateAssemblyService,
)
from services.extreme_sustained_dps_passive_rank_frontier_service import (
    ExtremeSustainedDPSPassiveRankCandidate,
)
from services.extreme_sustained_dps_potion_frontier_service import (
    ExtremeSustainedDPSPotionCandidate,
    ExtremeSustainedDPSPotionFamily,
)
from services.extreme_sustained_dps_skill_bar_frontier_service import (
    ExtremeSustainedDPSSkillAlternative,
    ExtremeSustainedDPSSkillBarLegalityContext,
    ExtremeSustainedDPSSkillBarState,
    ExtremeSustainedDPSTwoBarSkillCandidate,
)
from services.extreme_sustained_dps_weapon_poison_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonLoadoutCandidate,
    ExtremeSustainedDPSWeaponPoisonSelection,
)
from services.extreme_gear_bar_access_service import ExtremeGearBarAccess


def _skill(name, base_id):
    return ExtremeSustainedDPSSkillAlternative(
        ability_id=base_id + 1,
        base_ability_id=base_id,
        name=name,
        skill_line="Animal Companions",
        morph=1,
        ultimate=False,
    )


def _context(*, one_bar=False):
    build = PlayerBuild(
        EsoClass="Warden",
        Role="DD",
        Mundus="The Thief",
        Food="Existing Food",
    )
    build.FrontBarWeapon.Set = "Gear A"
    build.FrontBarWeapon.WeaponType = "Inferno Staff"
    build.BackBarWeapon.Set = "Gear B"
    build.BackBarWeapon.WeaponType = "Bow"
    progression = CharacterProgression(
        owned_skill_lines=("Fighters Guild",),
        passive_ranks={"Existing Passive": 1},
    )
    bars = ("front",) if one_bar else ("front", "back")
    access = ExtremeGearBarAccess(
        activatable_bars=bars,
        can_swap=not one_bar,
    )
    legality = ExtremeSustainedDPSSkillBarLegalityContext(
        character_class="Warden",
        owned_skill_lines=("Fighters Guild",),
    )
    return ExtremeSustainedDPSCrossAxisContext(
        build=build,
        progression=progression,
        front_skill_context=legality,
        back_skill_context=legality,
        bar_access=access,
        class_skill_lines=("animal_companions", "green_balance", "winters_embrace"),
        equipped_armor_lines=(),
        front_weapon_lines=("Destruction Staff",),
        back_weapon_lines=() if one_bar else ("Bow",),
        explicit_owned_skill_lines=("Fighters Guild",),
        one_bar_only=one_bar,
        evidence=(),
        unresolved=(),
    )


def _cp():
    build = PlayerBuild()
    build.ChampionPoints = [
        ChampionPointEntry(Name="Deadly Aim", Points="50"),
        ChampionPointEntry(Name="Thaumaturge", Points="50"),
    ]
    return ExtremeSustainedDPSChampionPointCandidate(
        structural_index=7,
        selected_star_names=("Deadly Aim", "Thaumaturge"),
        build=build,
    )


def _potion():
    family = ExtremeSustainedDPSPotionFamily(
        selected_label="alchemy_family:u50:increase_power+critical",
        traits=("Increase Power", "Critical"),
        formula_ids=("formula:x",),
    )
    return ExtremeSustainedDPSPotionCandidate(
        structural_index=3,
        family=family,
        build=PlayerBuild(Potion=family.selected_label),
    )


def _passives(*, erase_owned=False):
    progression = CharacterProgression(
        owned_skill_lines=() if erase_owned else ("Fighters Guild",),
        passive_ranks={"Existing Passive": 1, "Slayer": 3},
    )
    return ExtremeSustainedDPSPassiveRankCandidate(
        structural_index=11,
        selected_ranks=(("Slayer", 3),),
        progression=progression,
    )


def _poisons(*, back=True):
    front = ExtremeSustainedDPSWeaponPoisonSelection(
        selected_label="poison:front",
        formula=None,
    )
    back_selection = ExtremeSustainedDPSWeaponPoisonSelection(
        selected_label="poison:back" if back else "",
        formula=None,
    )
    return ExtremeSustainedDPSWeaponPoisonLoadoutCandidate(
        structural_index=5,
        front=front,
        back=back_selection,
        build=PlayerBuild(
            FrontBarPoison=front.selected_label,
            BackBarPoison=back_selection.selected_label,
        ),
    )


def _skills(*, back=True):
    front = ExtremeSustainedDPSSkillBarState((_skill("Skill A", 100),), None)
    back_state = (
        ExtremeSustainedDPSSkillBarState((_skill("Skill B", 200),), None)
        if back
        else ExtremeSustainedDPSSkillBarState((), None)
    )
    return ExtremeSustainedDPSTwoBarSkillCandidate(
        structural_index=13,
        front=front,
        back=back_state,
        build=PlayerBuild(),
    )


def test_assembly_applies_only_owned_axis_state_to_cross_axis_build() -> None:
    result = ExtremeSustainedDPSGeneratedCandidateAssemblyService.assemble(
        _context(),
        champion_points=_cp(),
        potion=_potion(),
        passive_ranks=_passives(),
        skills=_skills(),
    )

    assert result.resolved is True
    assert result.coordinate.identity == "cp:7|potion:3|passive:11|skills:13|poison:0"
    assert result.build.Mundus == "The Thief"
    assert result.build.Food == "Existing Food"
    assert result.build.FrontBarWeapon.Set == "Gear A"
    assert result.build.BackBarWeapon.Set == "Gear B"
    assert tuple(cp.Name for cp in result.build.ChampionPoints) == (
        "Deadly Aim",
        "Thaumaturge",
    )
    assert result.build.Potion.startswith("alchemy_family:")
    assert result.build.FrontBarSkills[0] == "Skill A"
    assert result.build.BackBarSkills[0] == "Skill B"
    assert result.progression.passive_rank("Slayer") == 3


def test_one_bar_context_rejects_nonempty_back_bar_choice() -> None:
    result = ExtremeSustainedDPSGeneratedCandidateAssemblyService.assemble(
        _context(one_bar=True),
        champion_points=_cp(),
        potion=_potion(),
        passive_ranks=_passives(),
        skills=_skills(back=True),
    )

    assert result.resolved is False
    assert any("One-bar" in row for row in result.unresolved)


def test_passive_candidate_cannot_erase_explicit_ownership() -> None:
    result = ExtremeSustainedDPSGeneratedCandidateAssemblyService.assemble(
        _context(),
        champion_points=_cp(),
        potion=_potion(),
        passive_ranks=_passives(erase_owned=True),
        skills=_skills(),
    )

    assert result.resolved is False
    assert any("erased explicit owned skill line" in row for row in result.unresolved)

def test_assembly_carries_only_poison_owned_bar_state() -> None:
    context = _context()
    context.build.FrontBarPoison = "baseline-front"
    context.build.BackBarPoison = "baseline-back"

    result = ExtremeSustainedDPSGeneratedCandidateAssemblyService.assemble(
        context,
        champion_points=_cp(),
        potion=_potion(),
        passive_ranks=_passives(),
        skills=_skills(),
        poison_loadout=_poisons(),
    )

    assert result.resolved is True
    assert result.coordinate.poison_index == 5
    assert result.coordinate.identity.endswith("|poison:5")
    assert result.build.FrontBarPoison == "poison:front"
    assert result.build.BackBarPoison == "poison:back"
    assert result.poison_loadout is not None
    assert result.poison_loadout.structural_index == 5
    assert result.poison_loadout.front.selected_label == "poison:front"
    assert result.poison_loadout.back.selected_label == "poison:back"
    assert result.build.FrontBarWeapon.Set == "Gear A"
    assert result.build.BackBarWeapon.Set == "Gear B"


def test_one_bar_context_rejects_nonempty_generated_back_bar_poison() -> None:
    result = ExtremeSustainedDPSGeneratedCandidateAssemblyService.assemble(
        _context(one_bar=True),
        champion_points=_cp(),
        potion=_potion(),
        passive_ranks=_passives(),
        skills=_skills(back=False),
        poison_loadout=_poisons(back=True),
    )

    assert result.resolved is False
    assert any("back-bar poison" in row for row in result.unresolved)

