from pathlib import Path

import pytest

from models.build_model import BuildContextVariant, BuildRoster, PlayerBuild
from services.build_reuse_service import BuildReuseService


def _healer() -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="SW Healer",
        EsoClass="Warden",
        Role="Healer",
        Race="Breton",
        AttributeMagicka=64,
        FrontBarSkills=["Combat Prayer", "Budding Seeds", "Energy Orb", "", "", ""],
        BackBarSkills=["Radiating Regeneration", "Illustrious Healing", "", "", "", ""],
        Food="Clockwork Citrus Filet",
        ReadyForRaid=True,
        ContextVariants=[
            BuildContextVariant(
                ContextType="Team + Boss",
                TeamName="Swine & Punishment",
                BossName="*",
                Notes="Bosses",
            )
        ],
    )


def test_exact_copy_changes_identity_but_preserves_build_configuration() -> None:
    source = _healer()
    result = BuildReuseService.copy_build(
        source,
        destination_name="Maeve",
        destination_gamertag="OtherPlayer",
        destination_class="Warden",
        destination_race="High Elf",
        destination_role="Healer",
        new_build_name="SW Healer Copy",
    )
    copied = result.build
    assert copied.Name == "Maeve"
    assert copied.Gamertag == "OtherPlayer"
    assert copied.Race == "High Elf"
    assert copied.ReadyForRaid is False
    assert copied.FrontBarSkills == source.FrontBarSkills
    assert copied.ContextVariants[0].BossName == "*"


def test_exact_copy_rejects_cross_class_identity() -> None:
    with pytest.raises(ValueError, match="same class"):
        BuildReuseService.copy_build(
            _healer(),
            destination_name="Arc Healer",
            destination_gamertag="OtherPlayer",
            destination_class="Arcanist",
        )


def test_template_keeps_role_base_and_class_overlay_separate(tmp_path: Path) -> None:
    service = BuildReuseService(tmp_path / "build_templates.json")
    template = service.save_template_from_build(_healer(), template_name="Core Healer")
    assert template.role == "Healer"
    assert "FrontBarSkills" not in template.base_payload
    assert template.class_overlays["Warden"]["FrontBarSkills"][0] == "Combat Prayer"
    assert service.load_templates()[0].name == "Core Healer"


def test_cross_class_template_application_fails_closed_on_skill_state(tmp_path: Path) -> None:
    service = BuildReuseService(tmp_path / "build_templates.json")
    template = service.save_template_from_build(_healer(), template_name="Core Healer")
    result = service.apply_template(
        template,
        destination_name="Arc Healer",
        destination_gamertag="OtherPlayer",
        destination_class="Arcanist",
        destination_role="Healer",
    )
    assert result.build.EsoClass == "Arcanist"
    assert result.build.FrontBarSkills == [""] * 6
    assert result.build.Food == "Clockwork Citrus Filet"
    assert result.warnings


def test_replace_or_append_is_keyed_by_player_character_build_name() -> None:
    source = _healer()
    roster = BuildRoster(Members=[source])
    replacement = _healer()
    replacement.Food = "Different Food"
    updated = BuildReuseService.replace_or_append(roster, replacement)
    assert len(updated.Members) == 1
    assert updated.Members[0].Food == "Different Food"
