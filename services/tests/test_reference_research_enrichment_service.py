from services.reference_research_enrichment_service import ReferenceResearchEnrichmentService


def test_status_effect_research_keeps_provenance_and_update_visible():
    facts = ReferenceResearchEnrichmentService().facts_for("Poisoned")

    assert len(facts) == 2
    assert {fact.label for fact in facts} == {"Delivery", "Additional behavior"}
    assert all(fact.game_update == "U41+" for fact in facts)
    assert all(fact.confidence == "high" for fact in facts)
    assert any("Update 41" in fact.source for fact in facts)
    assert any("100% bonus damage" in fact.value for fact in facts)


def test_unknown_entry_has_no_research_fact_instead_of_inventing_one():
    assert ReferenceResearchEnrichmentService().facts_for("Imaginary Status") == ()
