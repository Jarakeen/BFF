from services.ability_effect_provider_reference_service import AbilityEffectProviderReference
from ui.reference_data_model import ReferenceEntry
from ui.reference_provider_relationships import enrich_reference_entries_with_ability_providers


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
