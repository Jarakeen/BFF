from __future__ import annotations

from pathlib import Path

from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_promotion import build_encounter_promotion_preview
from tools.reconcile_encounter_evidence import _load_packet


PACKET = Path("data/encounter_evidence/graven_deep_boss3.json")


def test_zelvraak_packet_preserves_corroboration_and_inferno_conflict():
    payload, evidence = _load_packet(PACKET)
    facts = reconcile_encounter_evidence(evidence)
    candidates = build_encounter_promotion_preview(facts)

    assert payload["content_id"] == "graven_deep"
    assert payload["encounter_id"] == "zelvraak_the_unbreathing"
    assert len(facts) == 21

    by_ref = {
        f"{candidate.fact.fact_type}:{candidate.fact.fact_key}": candidate
        for candidate in candidates
    }

    eligible_refs = {
        "mechanic_state:heavy_cone_exists",
        "mechanic_detail:heavy_cone_tank_behavior",
        "mechanic_state:sea_orbs_exist",
        "failure_condition:sea_orb_reaches_ground_party_wipe",
        "mechanic_detail:sea_orb_hardmode_count",
        "mechanic_detail:sea_orb_veteran_count",
        "phase:afterlife_phase",
        "mechanic_detail:afterlife_healing_ghosts",
        "mechanic_state:fractured_souls_exist",
        "mechanic_detail:fractured_souls_affect_post_afterlife_add",
        "mechanic_state:split_exists",
        "mechanic_detail:split_four_interruptible_shades",
        "transition:split_thresholds",
        "mechanic_state:inferno_exists",
    }
    for ref in eligible_refs:
        assert by_ref[ref].promotion_status == "eligible"

    inferno = by_ref["mechanic_detail:inferno_response"]
    assert inferno.fact.status == "conflicting"
    assert inferno.promotion_status == "blocked"
    assert inferno.fact.distinct_values == 2

    assert sum(c.promotion_status == "eligible" for c in candidates) == 14
    assert sum(c.promotion_status == "review_required" for c in candidates) == 6
    assert sum(c.promotion_status == "blocked" for c in candidates) == 1
