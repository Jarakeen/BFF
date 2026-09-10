from services.passive_effect_provider_reference_service import PassiveEffectProviderReference
from ui.reference_data_model import ReferenceEntry
from ui.reference_provider_relationships import enrich_reference_entries_with_passive_providers


def _entry(name: str, entry_type: str = "Named Effect") -> ReferenceEntry:
    return ReferenceEntry(
        name=name,
        entry_type=entry_type,
        source_scope="Global Combat",
        tags=("NAMED EFFECT",) if entry_type == "Named Effect" else ("MECHANIC",),
        summary="test",
        details=(("Authority", "Canonical named-effect semantics"),),
    )


def test_reviewed_passive_provider_is_exposed_with_condition_and_rank_duration():
    provider = PassiveEffectProviderReference(
        passive_key="accelerated_growth",
        passive_name="Accelerated Growth",
        eso_class="Warden",
        skill_line="Green Balance",
        effect_name="Major Mending",
        relationship="Grants",
        condition="Heal a target under 40% Health with a Green Balance ability.",
        target="Self",
        duration_rank_1=2.0,
        duration_rank_2=4.0,
        evidence=("reviewed passive evidence",),
    )

    result = enrich_reference_entries_with_passive_providers((_entry("Major Mending"),), (provider,))[0]
    text = result.detail_text()

    assert "Reviewed passive providers" in text
    assert "Accelerated Growth [accelerated_growth]" in text
    assert "Warden / Green Balance" in text
    assert "rank 1: 2s; rank 2: 4s" in text
    assert "under 40% Health" in text
    assert "Accelerated Growth" in result.related
    assert "reviewed passive evidence" in result.evidence


def test_named_effect_without_reviewed_passive_provider_gets_specific_open_gap():
    result = enrich_reference_entries_with_passive_providers((_entry("Major Courage"),), ())[0]

    assert "Passive provider coverage" in result.detail_text()
    assert "research remains open" in result.detail_text()
    assert "Not modeled" not in result.detail_text()


def test_non_named_reference_entry_does_not_get_passive_provider_gap_noise():
    mechanic = _entry("Heavy Attack — Test Boss", entry_type="Mechanic")

    result = enrich_reference_entries_with_passive_providers((mechanic,), ())[0]

    assert "Passive provider coverage" not in result.detail_text()
