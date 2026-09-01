from __future__ import annotations

from pathlib import Path

from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_promotion import build_encounter_promotion_preview
from tools.reconcile_encounter_evidence import _load_packet


PACKET = Path("data/encounter_evidence/graven_deep_boss1.json")


def test_euphotic_gatekeeper_packet_preserves_corroboration_and_review_boundaries():
    payload, evidence = _load_packet(PACKET)
    facts = reconcile_encounter_evidence(evidence)
    candidates = build_encounter_promotion_preview(facts)

    assert payload["content_id"] == "graven_deep"
    assert payload["encounter_id"] == "the_euphotic_gatekeeper"
    assert len(facts) == 11

    by_ref = {
        f"{candidate.fact.fact_type}:{candidate.fact.fact_key}": candidate
        for candidate in candidates
    }

    eligible_refs = {
        "mechanic_state:bristlebarb_exists",
        "mechanic_state:pangrit_den_exists",
        "mechanic_detail:bristlebarb_poison_closes_pangrit_den",
        "mechanic_state:charge_exists",
        "mechanic_detail:charge_knockback",
        "mechanic_detail:charge_emits_aoes",
        "mechanic_detail:teleport_afterimage_explosion",
    }
    for ref in eligible_refs:
        assert by_ref[ref].promotion_status == "eligible"

    review_refs = {
        "mechanic_detail:health_by_difficulty_uesp",
        "mechanic_state:bristlepitch_hazard_exists",
        "mechanic_state:leap_exists",
        "mechanic_state:heavy_attack_exists",
    }
    for ref in review_refs:
        assert by_ref[ref].promotion_status == "review_required"

    assert sum(c.promotion_status == "eligible" for c in candidates) == 7
    assert sum(c.promotion_status == "review_required" for c in candidates) == 4
    assert sum(c.promotion_status == "blocked" for c in candidates) == 0
