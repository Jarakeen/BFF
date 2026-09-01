from __future__ import annotations

from pathlib import Path

from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_promotion import build_encounter_promotion_preview
from tools.reconcile_encounter_evidence import _load_packet


PACKET = Path("data/encounter_evidence/rockgrove_boss1.json")


def test_oaxiltso_packet_preserves_corroboration_and_threshold_conflict():
    payload, evidence = _load_packet(PACKET)
    facts = reconcile_encounter_evidence(evidence)
    candidates = build_encounter_promotion_preview(facts)

    assert payload["content_id"] == "rockgrove"
    assert payload["encounter_id"] == "oaxiltso"
    assert len(facts) == 16

    by_ref = {
        f"{candidate.fact.fact_type}:{candidate.fact.fact_key}": candidate
        for candidate in candidates
    }

    assert by_ref["mechanic_state:noxious_sludge_exists"].promotion_status == "eligible"
    assert by_ref["mechanic_detail:noxious_sludge_core_behavior"].promotion_status == "eligible"
    assert by_ref["mechanic_state:savage_blitz_exists"].promotion_status == "eligible"
    assert by_ref["mechanic_detail:savage_blitz_targeting"].promotion_status == "eligible"
    assert by_ref["mechanic_state:fiery_stomp_exists"].promotion_status == "eligible"
    assert by_ref["mechanic_detail:fiery_stomp_fire_waves"].promotion_status == "eligible"
    assert by_ref["mechanic_state:havocrel_annihilator_summons_exist"].promotion_status == "eligible"
    assert by_ref["mechanic_state:proximity_enrage_exists"].promotion_status == "eligible"

    threshold = by_ref["transition:havocrel_annihilator_spawn_thresholds"]
    assert threshold.fact.status == "conflicting"
    assert threshold.promotion_status == "blocked"
    assert threshold.fact.distinct_values == 2

    assert sum(c.promotion_status == "eligible" for c in candidates) == 8
    assert sum(c.promotion_status == "review_required" for c in candidates) == 7
    assert sum(c.promotion_status == "blocked" for c in candidates) == 1
