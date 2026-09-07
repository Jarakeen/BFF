from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.minmax_character_progression_adapter import SavedBuildProgressionResolution
from services.rotation_progression_readiness_service import RotationProgressionReadinessService


class _Adapter:
    def __init__(self, resolution):
        self.resolution = resolution

    def resolve(self, build):
        return self.resolution


def _build() -> PlayerBuild:
    build = PlayerBuild()
    build.Name = "Magrat"
    build.BuildName = "DF Healer"
    build.Armor["Chest"]["Weight"] = "Light"
    build.Armor["Head"]["Weight"] = "Medium"
    return build


def test_magicka_readiness_requires_canonical_light_armor_when_equipped() -> None:
    service = RotationProgressionReadinessService(
        _Adapter(
            SavedBuildProgressionResolution(
                character_id="char-magrat",
                progression=CharacterProgression(
                    attributes=AttributeAllocation(magicka=64),
                    owned_skill_lines=("Restoration Staff",),
                ),
            )
        )
    )

    result = service.assess(build=_build(), resource=ResourceType.MAGICKA)

    assert result.equipped_armor_skill_lines == ("Light Armor", "Medium Armor")
    assert result.cost_relevant_skill_lines == ("Light Armor",)
    assert result.missing_cost_relevant_skill_lines == ("Light Armor",)
    assert result.ready is False


def test_magicka_readiness_is_green_when_canonical_light_armor_is_owned() -> None:
    service = RotationProgressionReadinessService(
        _Adapter(
            SavedBuildProgressionResolution(
                character_id="char-magrat",
                progression=CharacterProgression(
                    attributes=AttributeAllocation(magicka=64),
                    owned_skill_lines=("Light Armor", "Restoration Staff"),
                ),
            )
        )
    )

    result = service.assess(build=_build(), resource=ResourceType.MAGICKA)

    assert result.missing_cost_relevant_skill_lines == ()
    assert result.unresolved == ()
    assert result.ready is True


def test_empty_canonical_progression_stays_explicit_and_never_infers_ownership() -> None:
    service = RotationProgressionReadinessService(
        _Adapter(
            SavedBuildProgressionResolution(
                character_id="char-magrat",
                progression=CharacterProgression(attributes=AttributeAllocation(magicka=64)),
            )
        )
    )

    result = service.assess(build=_build(), resource=ResourceType.MAGICKA)

    assert result.canonical_owned_skill_lines == ()
    assert result.missing_cost_relevant_skill_lines == ("Light Armor",)
    assert any("no owned skill lines recorded" in item for item in result.unresolved)
    assert result.ready is False


def test_stamina_readiness_tracks_medium_armor_independently() -> None:
    service = RotationProgressionReadinessService(
        _Adapter(
            SavedBuildProgressionResolution(
                character_id="char-magrat",
                progression=CharacterProgression(
                    attributes=AttributeAllocation(stamina=64),
                    owned_skill_lines=("Light Armor",),
                ),
            )
        )
    )

    result = service.assess(build=_build(), resource=ResourceType.STAMINA)

    assert result.cost_relevant_skill_lines == ("Medium Armor",)
    assert result.missing_cost_relevant_skill_lines == ("Medium Armor",)
    assert result.ready is False
