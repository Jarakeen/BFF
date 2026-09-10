from services.reference_research_enrichment_service import ReferenceResearchEnrichmentService


def test_status_effect_research_keeps_provenance_and_update_visible():
    facts = ReferenceResearchEnrichmentService().facts_for("Poisoned")

    assert len(facts) == 2
    assert {fact.label for fact in facts} == {"Delivery", "Additional behavior"}
    assert all(fact.game_update == "U41+" for fact in facts)
    assert all(fact.confidence == "high" for fact in facts)
    assert any("Update 41" in fact.source for fact in facts)
    assert any("100% bonus damage" in fact.value for fact in facts)


def test_off_balance_uses_official_timing_and_lockout_evidence():
    facts = ReferenceResearchEnrichmentService().facts_for("Off Balance")
    values = " ".join(fact.value for fact in facts)

    assert len(facts) == 3
    assert "7 seconds" in values
    assert "15 seconds" in values
    assert "do not consume Off Balance" in values
    assert all(fact.source_tier == "official" for fact in facts)


def test_dreadsail_debuffs_keep_encounter_scope_and_confidence_visible():
    facts = ReferenceResearchEnrichmentService().facts_for("Devitalized")
    values = " ".join(fact.value for fact in facts)

    assert len(facts) == 2
    assert "Dreadsail Reef" in values
    assert "Resistance are reduced by 60%" in values
    assert "damage taken is increased by 30%" in values
    assert all(fact.confidence == "medium-high" for fact in facts)


def test_unknown_entry_has_no_research_fact_instead_of_inventing_one():
    assert ReferenceResearchEnrichmentService().facts_for("Imaginary Status") == ()
