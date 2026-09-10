from services.reference_research_enrichment_service import ReferenceResearchEnrichmentService


def test_deadstar_research_marks_movement_without_inventing_target_count():
    facts = ReferenceResearchEnrichmentService().facts_for("Deadstar — Xalvakka")

    assert any(fact.replaces_label == "Requires movement" for fact in facts)
    assert any("three sequential meteors" in fact.value.lower() for fact in facts)
    assert not any(fact.replaces_label == "Target count" for fact in facts)


def test_soul_resonance_research_identifies_purge_created_hazard():
    facts = ReferenceResearchEnrichmentService().facts_for("Soul Resonance — Xalvakka")

    assert any(
        fact.replaces_label == "Persistent hazard" and "Corrupted Azureplasm" in fact.value
        for fact in facts
    )
    assert any("Soul Purge" in fact.value for fact in facts)


def test_wraith_and_split_research_capture_failure_and_floor_state():
    service = ReferenceResearchEnrichmentService()
    wraiths = service.facts_for("Summon Wraiths — Xalvakka")
    split = service.facts_for("Split — Xalvakka")

    assert any(fact.replaces_label == "Failure is fatal" for fact in wraiths)
    assert any(fact.replaces_label == "Persistent hazard" for fact in split)
    assert any(fact.replaces_label == "Requires movement" for fact in split)
