from models.build_model import GearSlot, PlayerBuild
from services.rotation_saved_build_bloodthirsty_service import (
    RotationSavedBuildBloodthirstyService,
)


class _Repository:
    def get_bloodthirsty_max_damage(self, *, quality, level):
        if str(level).casefold() != "cp160":
            return None
        return {
            "white": 70.0,
            "green": 140.0,
            "blue": 210.0,
            "purple": 280.0,
            "gold": 350.0,
        }.get(str(quality).casefold())


def _jewelry(*, trait="Bloodthirsty", quality="Gold", level="CP160") -> GearSlot:
    return GearSlot(
        Set="Test Set",
        Trait=trait,
        Quality=quality,
        Level=level,
    )


def test_three_gold_bloodthirsty_items_sum_their_static_ceiling() -> None:
    build = PlayerBuild(
        Necklace=_jewelry(),
        Ring1=_jewelry(),
        Ring2=_jewelry(),
    )
    result = RotationSavedBuildBloodthirstyService(
        repository=_Repository(),  # type: ignore[arg-type]
    ).resolve(build)

    assert result.resolved is True
    assert result.unresolved == ()
    assert [source.slot_name for source in result.sources] == [
        "Necklace",
        "Ring 1",
        "Ring 2",
    ]
    assert result.total_max_weapon_spell_damage == 1050.0


def test_non_bloodthirsty_jewelry_is_not_counted() -> None:
    build = PlayerBuild(
        Necklace=_jewelry(trait="Infused"),
        Ring1=_jewelry(),
    )
    result = RotationSavedBuildBloodthirstyService(
        repository=_Repository(),  # type: ignore[arg-type]
    ).resolve(build)

    assert result.resolved is True
    assert len(result.sources) == 1
    assert result.total_max_weapon_spell_damage == 350.0


def test_unverified_level_fails_closed() -> None:
    build = PlayerBuild(Ring2=_jewelry(level="CP70"))
    result = RotationSavedBuildBloodthirstyService(
        repository=_Repository(),  # type: ignore[arg-type]
    ).resolve(build)

    assert result.resolved is False
    assert result.sources == ()
    assert result.unresolved == (
        "Ring 2 Bloodthirsty magnitude requires CP160 supported-quality evidence (CP70, Gold)",
    )


def test_real_repository_exposes_current_gold_cp160_ceiling() -> None:
    result = RotationSavedBuildBloodthirstyService("data/eso.db").resolve(
        PlayerBuild(Ring1=_jewelry())
    )

    assert result.resolved is True
    assert result.total_max_weapon_spell_damage == 350.0
