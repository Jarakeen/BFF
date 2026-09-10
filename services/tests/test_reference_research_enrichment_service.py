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


def test_component_named_effects_get_human_readable_standard_values():
    service = ReferenceResearchEnrichmentService()

    assert service.facts_for("Major Berserk")[0].value == "Increases damage done by 10%."
    assert service.facts_for("Minor Protection")[0].value == "Reduces damage taken by 5%."
    assert service.facts_for("Major Vulnerability")[0].value == "Increases damage taken by 10%."
    assert "Dungeon, Trial, and Arena" in service.facts_for("Major Slayer")[0].value
    assert "12%" in service.facts_for("Major Vitality")[0].value
    assert "damage shield strength" in service.facts_for("Major Vitality")[0].value


def test_u41_vitality_and_defile_research_uses_current_shield_semantics():
    service = ReferenceResearchEnrichmentService()

    vitality = service.facts_for("Minor Vitality")[0]
    defile = service.facts_for("Minor Defile")[0]

    assert vitality.game_update == "U41+"
    assert defile.game_update == "U41+"
    assert "6%" in vitality.value
    assert "6%" in defile.value
    assert "damage shield strength" in vitality.value
    assert "damage shield strength" in defile.value
    assert "Health Recovery" not in defile.value


def test_unknown_entry_has_no_research_fact_instead_of_inventing_one():
    assert ReferenceResearchEnrichmentService().facts_for("Imaginary Status") == ()
