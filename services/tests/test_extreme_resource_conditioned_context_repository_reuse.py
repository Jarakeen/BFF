from minmax.gear_set_repository import GearSetRepository
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedPhase5ContextFactory,
)


def test_conditioned_factories_reuse_static_gear_input_repositories_per_database(tmp_path) -> None:
    database = tmp_path / "eso.db"

    first = ExtremeResourceConditionedPhase5ContextFactory(
        gear_set_repository=GearSetRepository(database),
    )
    second = ExtremeResourceConditionedPhase5ContextFactory(
        gear_set_repository=GearSetRepository(database),
    )

    assert first.gear_resolver is not None
    assert second.gear_resolver is not None
    assert first.gear_resolver.armor_glyph_repository is second.gear_resolver.armor_glyph_repository
    assert first.gear_resolver.jewelry_glyph_repository is second.gear_resolver.jewelry_glyph_repository
    assert first.gear_resolver.jewelry_trait_repository is second.gear_resolver.jewelry_trait_repository
    assert first.skill_line_repository is second.skill_line_repository
    assert first.racial_passive_repository is second.racial_passive_repository


def test_conditioned_factories_do_not_share_static_gear_inputs_across_databases(tmp_path) -> None:
    first = ExtremeResourceConditionedPhase5ContextFactory(
        gear_set_repository=GearSetRepository(tmp_path / "one.db"),
    )
    second = ExtremeResourceConditionedPhase5ContextFactory(
        gear_set_repository=GearSetRepository(tmp_path / "two.db"),
    )

    assert first.gear_resolver is not None
    assert second.gear_resolver is not None
    assert first.gear_resolver.armor_glyph_repository is not second.gear_resolver.armor_glyph_repository
    assert first.gear_resolver.jewelry_glyph_repository is not second.gear_resolver.jewelry_glyph_repository
    assert first.gear_resolver.jewelry_trait_repository is not second.gear_resolver.jewelry_trait_repository
    assert first.skill_line_repository is not second.skill_line_repository
    assert first.racial_passive_repository is not second.racial_passive_repository
