from services.reference_research_enrichment_service import ReferenceResearchEnrichmentService


def _facts(name: str):
    return ReferenceResearchEnrichmentService().facts_for(name)


def test_oaxiltso_noxious_sludge_exposes_damage_targeting_and_pool_rules():
    facts = _facts("Noxious Sludge — Oaxiltso")
    values = " ".join(fact.value for fact in facts)

    assert any(fact.replaces_label == "Damage type" for fact in facts)
    assert "Two players are selected" in values
    assert "ramping Poison damage" in values
    assert "temporarily poisons that pool" in values


def test_oaxiltso_savage_blitz_preserves_path_hazard_instead_of_fake_target_count():
    facts = _facts("Savage Blitz — Oaxiltso")
    values = " ".join(fact.value for fact in facts)

    assert "farthest target within 25 meters" in values
    assert "charge path" in values
    assert all(fact.replaces_label != "Target count" for fact in facts)


def test_bahsei_prime_meteor_exposes_movement_and_wipe_failure_window():
    facts = _facts("Meteor Swarm — Flame-Herald Bahsei")
    values = " ".join(fact.value for fact in facts)

    assert any(fact.replaces_label == "Requires movement" for fact in facts)
    assert any(fact.replaces_label == "Failure is fatal" for fact in facts)
    assert "10-second window" in values
    assert "Prime Meteor" in values


def test_bahsei_health_threshold_add_sequences_are_explicit():
    abominations = " ".join(fact.value for fact in _facts("Summoning Runes — Flame-Herald Bahsei"))
    behemoths = " ".join(fact.value for fact in _facts("Summon Behemoth — Flame-Herald Bahsei"))

    assert "90%, 85%, 80%, 75%, 70%, 65%, and 60%" in abominations
    assert "50%, 40%, 25%, 20%, and 10%" in behemoths
