from minmax.skill_component_classification import HealTemporalScope, SkillEffectKind
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


class _EmptyBase:
    def get_for_skill_rank(self, skill_rank_id: int):
        return ()


class _BaseWithSentinel:
    def get_for_skill_rank(self, skill_rank_id: int):
        from minmax.skill_component_classification import SkillComponentClassification

        return (
            SkillComponentClassification(
                skill_rank_id=skill_rank_id,
                coefficient_number=99,
                effect_kind=SkillEffectKind.UTILITY,
                source="base sentinel",
            ),
        )


def _repo(base=None):
    return RotationHealerU50SkillComponentRepository(
        "unused.db",
        base_repository=base or _EmptyBase(),
    )


def test_budding_seeds_bloom_is_delayed_heal_and_field_is_periodic():
    components = _repo().get_for_skill_rank(
        RotationHealerU50SkillComponentRepository.BUDDING_SEEDS_RANK_ID
    )
    by_number = {item.coefficient_number: item for item in components}

    assert by_number[1].effect_kind is SkillEffectKind.HEAL
    assert by_number[1].heal_temporal_scope is HealTemporalScope.DELAYED
    assert by_number[1].is_dot is False
    assert by_number[2].effect_kind is SkillEffectKind.HEAL
    assert by_number[2].heal_temporal_scope is HealTemporalScope.PERIODIC
    assert by_number[2].is_dot is True


def test_budding_seeds_harvest_synergy_is_not_routed_as_caster_owned_heal():
    repo = _repo()
    components = repo.get_for_skill_rank(repo.BUDDING_SEEDS_RANK_ID)

    assert {item.coefficient_number for item in components} == {1, 2}
    assert repo.is_intentionally_excluded_caster_healing_component(
        skill_rank_id=repo.BUDDING_SEEDS_RANK_ID,
        coefficient_number=3,
    ) is True


def test_energy_orb_routes_periodic_orb_but_not_healing_combustion_synergy():
    repo = _repo()
    components = repo.get_for_skill_rank(repo.ENERGY_ORB_RANK_ID)

    assert len(components) == 1
    assert components[0].coefficient_number == 1
    assert components[0].heal_temporal_scope is HealTemporalScope.PERIODIC
    assert repo.is_intentionally_excluded_caster_healing_component(
        skill_rank_id=repo.ENERGY_ORB_RANK_ID,
        coefficient_number=2,
    ) is True


def test_unknown_component_is_not_treated_as_intentional_caster_exclusion():
    assert _repo().is_intentionally_excluded_caster_healing_component(
        skill_rank_id=123456,
        coefficient_number=7,
    ) is False


def test_common_df_healer_hots_are_periodic():
    repo = _repo()
    ranks = (
        repo.RADIATING_REGENERATION_RANK_ID,
        repo.ILLUSTRIOUS_HEALING_RANK_ID,
        repo.ENERGY_ORB_RANK_ID,
        repo.ECHOING_VIGOR_RANK_ID,
    )

    for rank_id in ranks:
        component = repo.get_for_skill_rank(rank_id)[0]
        assert component.effect_kind is SkillEffectKind.HEAL
        assert component.heal_temporal_scope is HealTemporalScope.PERIODIC
        assert component.is_dot is True


def test_combat_prayer_is_direct_heal():
    component = _repo().get_for_skill_rank(
        RotationHealerU50SkillComponentRepository.COMBAT_PRAYER_RANK_ID
    )[0]

    assert component.effect_kind is SkillEffectKind.HEAL
    assert component.heal_temporal_scope is HealTemporalScope.DIRECT
    assert component.is_dot is False


def test_unrelated_base_components_are_preserved():
    components = _repo(_BaseWithSentinel()).get_for_skill_rank(123456)

    assert len(components) == 1
    assert components[0].coefficient_number == 99
    assert components[0].effect_kind is SkillEffectKind.UTILITY
