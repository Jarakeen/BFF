from minmax.character_progression import AttributeAllocation, CharacterProgression
from models.build_model import PlayerBuild
from services.minmax_character_progression_adapter import SavedBuildProgressionResolution
from services.rotation_sustain_service import RotationSustainService


class _Adapter:
    def __init__(self, resolution):
        self.resolution = resolution

    def resolve(self, build):
        return self.resolution


def _build() -> PlayerBuild:
    build = PlayerBuild()
    build.Name = "Magrat"
    build.BuildName = "DF Healer"
    build.AttributeMagicka = 64
    build.Armor["Chest"]["Weight"] = "Light"
    build.Armor["Head"]["Weight"] = "Medium"
    return build


def test_rotation_sustain_prefers_canonical_owned_skill_lines() -> None:
    canonical = CharacterProgression(
        attributes=AttributeAllocation(magicka=64),
        owned_skill_lines=("Light Armor", "Restoration Staff"),
    )
    service = RotationSustainService(
        progression_adapter=_Adapter(
            SavedBuildProgressionResolution(
                character_id="char-magrat",
                progression=canonical,
            )
        )
    )

    progression, unresolved = service._progression(_build())

    assert progression.owns_skill_line("Light Armor")
    assert progression.owns_skill_line("Restoration Staff")
    assert progression.owns_skill_line("Medium Armor") is False
    assert unresolved == ()


def test_empty_canonical_progression_uses_labeled_compatibility_fallback() -> None:
    canonical = CharacterProgression(attributes=AttributeAllocation(magicka=64))
    service = RotationSustainService(
        progression_adapter=_Adapter(
            SavedBuildProgressionResolution(
                character_id="char-magrat",
                progression=canonical,
            )
        )
    )

    progression, unresolved = service._progression(_build())

    assert progression.owns_skill_line("Light Armor")
    assert progression.owns_skill_line("Medium Armor")
    assert any("canonical character progression has no owned skill lines" in item for item in unresolved)
    assert any("compatibility fallback" in item for item in unresolved)


def test_missing_canonical_character_keeps_resolution_failure_and_labels_fallback() -> None:
    fallback = CharacterProgression(
        attributes=AttributeAllocation(magicka=64),
        passive_ranks=None,
        passive_cp_points=None,
    )
    service = RotationSustainService(
        progression_adapter=_Adapter(
            SavedBuildProgressionResolution(
                character_id="",
                progression=fallback,
                unresolved=("Canonical character progression could not be resolved for saved build",),
            )
        )
    )

    progression, unresolved = service._progression(_build())

    assert progression.owns_skill_line("Light Armor")
    assert progression.owns_skill_line("Medium Armor")
    assert "Canonical character progression could not be resolved for saved build" in unresolved
    assert any("could not use canonical character progression" in item for item in unresolved)
