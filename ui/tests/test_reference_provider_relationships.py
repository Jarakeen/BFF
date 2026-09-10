from services.ability_effect_provider_reference_service import AbilityEffectProviderReference
from services.nonability_effect_provider_reference_service import NonAbilityEffectProviderReference
from ui.reference_data_model import ReferenceEntry
from ui.reference_provider_relationships import (
    enrich_reference_entries_with_ability_providers,
    enrich_reference_entries_with_nonability_providers,
    mark_passive_provider_gap,
)


def _entry(name: str) -> ReferenceEntry:
    return ReferenceEntry(
        name=name,
        entry_type="Named Effect",
        source_scope="Global Combat",
        tags=("NAMED EFFECT",),
        summary="test",
        details=(("Authority", "Canonical named-effect semantics"),),
    )


def test_enrichment_adds_only_reviewed_exact_effect_providers():
    entries = (_entry("Major Force"), _entry("Major Courage"))
    providers = (
        AbilityEffectProviderReference(
            ability_key="aggressive_horn",
            ability_name="Aggressive Horn",
            effect_name="Major Force",
            relationship="Grants",
            source="ESO-Hub",
            confidence="explicit",
        ),
    )

    result = enrich_reference_entries_with_ability_providers(entries, providers)
    by_name = {entry.name: entry for entry in result}

    assert "Reviewed ability providers" in by_name["Major Force"].detail_text()
    assert "Aggressive Horn [aggressive_horn]" in by_name["Major Force"].detail_text()
    assert "Aggressive Horn" in by_name["Major Force"].related
    assert "ability_combat_effect" in " ".join(by_name["Major Force"].evidence)
    assert "Reviewed ability providers" not in by_name["Major Courage"].detail_text()


def test_enrichment_keeps_weapon_and_condition_evidence_visible():
    entry = _entry("Off Balance")
    provider = AbilityEffectProviderReference(
        ability_key="crushing_shock",
        ability_name="Crushing Shock",
        effect_name="Off Balance",
        relationship="Applies",
        weapon_type="Lightning Staff",
        condition="Target must be interrupted while spellcasting",
        source="ESO Wiki",
        confidence="explicit",
    )

    result = enrich_reference_entries_with_ability_providers((entry,), (provider,))[0]
    text = result.detail_text()

    assert "weapon: Lightning Staff" in text
    assert "condition: Target must be interrupted while spellcasting" in text
    assert "confidence: explicit" in text


def test_nonability_enrichment_adds_reviewed_gear_and_potion_sources():
    entry = _entry("Major Courage")
    providers = (
        NonAbilityEffectProviderReference(
            source_kind="gear_set",
            source_key="gear_set:spell_power_cure",
            source_name="Spell Power Cure",
            effect_key="major_courage",
            relationship="Provides",
            piece_count=5,
            trigger="overheal_self_or_ally",
            duration=5.0,
            evidence="Canonical registry: minmax.gear_set_known_effects",
        ),
        NonAbilityEffectProviderReference(
            source_kind="potion_trait",
            source_key="alchemy_trait:test_courage",
            source_name="Test Courage",
            effect_key="major_courage",
            relationship="Grants",
            update="U50",
            evidence="Canonical module: minmax.alchemy_potion_buff_semantics",
        ),
    )

    result = enrich_reference_entries_with_nonability_providers((entry,), providers)[0]
    text = result.detail_text()

    assert "Reviewed gear providers" in text
    assert "Spell Power Cure (5-piece)" in text
    assert "trigger: overheal self or ally" in text
    assert "Reviewed potion providers" in text
    assert "Potion trait: Test Courage" in text
    assert "Spell Power Cure" in result.related
    assert "gear_set_known_effects" in " ".join(result.evidence)


def test_passive_provider_gap_is_explicit_only_for_named_effect_entries():
    named = _entry("Major Courage")
    mechanic = ReferenceEntry(
        name="Heavy Attack — Test Boss",
        entry_type="Mechanic",
        source_scope="Trial",
        tags=("MECHANIC",),
        summary="test",
        details=(("Authority", "Canonical encounter data"),),
    )

    named_result, mechanic_result = mark_passive_provider_gap((named, mechanic))

    assert "Passive provider coverage" in named_result.detail_text()
    assert "Not yet available" in named_result.detail_text()
    assert "Passive provider coverage" not in mechanic_result.detail_text()
