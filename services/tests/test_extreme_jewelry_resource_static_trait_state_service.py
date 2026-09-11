from models.build_model import PlayerBuild
from services.extreme_jewelry_resource_static_trait_state_service import (
    ExtremeJewelryResourceStaticTraitStateService,
)


def _service():
    return ExtremeJewelryResourceStaticTraitStateService(database_path="fake.db")


def test_max_health_selects_healthy_on_all_three_jewelry_slots():
    catalog = _service().build("max_health")

    assert catalog.denominator_proven
    assert catalog.relevant_traits == ("Healthy", "Triune")
    assert catalog.raw_loadouts_reviewed == 6 ** 3
    assert catalog.objective_relevant_loadouts_considered == 3 ** 3
    assert len(catalog.states) == 1
    state = catalog.states[0]
    assert state.traits == (
        ("Necklace", "Healthy"),
        ("Ring1", "Healthy"),
        ("Ring2", "Healthy"),
    )
    assert state.direct_delta == 3 * 965.0


def test_magicka_and_stamina_choose_their_stronger_single_resource_traits():
    magicka = _service().build("max_magicka").states[0]
    stamina = _service().build("max_stamina").states[0]

    assert {trait for _, trait in magicka.traits} == {"Arcane"}
    assert magicka.direct_delta == 3 * 877.0
    assert {trait for _, trait in stamina.traits} == {"Robust"}
    assert stamina.direct_delta == 3 * 877.0


def test_materialization_preserves_sets_and_enchants_but_sets_gold_cp160_trait_state():
    state = _service().build("max_health").states[0]
    build = PlayerBuild()
    for slot_name in ("Necklace", "Ring1", "Ring2"):
        slot = getattr(build, slot_name)
        slot.Set = "Test Set"
        slot.Enchant = "Health Recovery"

    materialized = ExtremeJewelryResourceStaticTraitStateService.materialize(build, state)

    for slot_name in ("Necklace", "Ring1", "Ring2"):
        slot = getattr(materialized, slot_name)
        assert slot.Set == "Test Set"
        assert slot.Enchant == "Health Recovery"
        assert slot.Trait == "Healthy"
        assert slot.Quality == "Gold"
        assert slot.Level == "CP160"


def test_static_trait_catalog_does_not_claim_glyph_dependent_infused():
    catalog = _service().build("max_health")

    assert "Infused" not in catalog.traits_reviewed
    assert "Infused" not in catalog.relevant_traits


def test_unreviewed_objective_fails_closed():
    try:
        _service().build("spell_damage")
    except KeyError as exc:
        assert "unreviewed Extreme jewelry resource trait objective" in str(exc)
    else:
        raise AssertionError("expected unsupported jewelry resource trait objective to fail closed")
