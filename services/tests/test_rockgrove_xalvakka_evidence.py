from __future__ import annotations

from pathlib import Path

from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_promotion import build_encounter_promotion_preview
from tools.reconcile_encounter_evidence import _load_packet


PACKET = Path("data/encounter_evidence/rockgrove_boss3.json")


def test_xalvakka_packet_preserves_corroborated_phase_and_wipe_structure():
    payload, evidence = _load_packet(PACKET)
    facts = reconcile_encounter_evidence(evidence)
    candidates = build_encounter_promotion_preview(facts)

    assert payload["content_id"] == "rockgrove"
    assert payload["encounter_id"] == "xalvakka"
    assert len(facts) == 20

    by_ref = {
        f"{candidate.fact.fact_type}:{candidate.fact.fact_key}": candidate
        for candidate in candidates
    }

    eligible = (
        "mechanic_state:wraith_summons_exist",
        "failure_condition:wraith_empowerment_unbreakable_shield_wipe",
        "mechanic_state:soul_resonance_exists",
        "mechanic_detail:soul_purge_blob_behavior",
        "mechanic_state:retreat_exists",
        "transition:retreat_thresholds",
        "failure_condition:retreat_lava_catches_left_behind_players",
        "phase:phase_2",
        "phase:phase_3",
        "mechanic_state:split_exists",
        "mechanic_detail:split_real_copy_detection",
        "mechanic_detail:phase_2_floor_fire_during_split",
        "mechanic_state:phase_3_meteors_exist",
        "mechanic_state:havocrel_goliath_summons_exist",
    )
    for ref in eligible:
        assert by_ref[ref].promotion_status == "eligible"

    retreat = by_ref["transition:retreat_thresholds"].fact
    assert retreat.value == {"thresholds": ["70%", "40%"]}
    assert retreat.status == "corroborated"

    wipe = by_ref[
        "failure_condition:wraith_empowerment_unbreakable_shield_wipe"
    ].fact
    assert wipe.value["unbreakable_shield"] is True
    assert wipe.value["party_wipe"] is True

    assert by_ref[
        "mechanic_detail:hardmode_lava_timer_xynode"
    ].promotion_status == "review_required"

    assert sum(c.promotion_status == "eligible" for c in candidates) == 14
    assert sum(c.promotion_status == "review_required" for c in candidates) == 6
    assert sum(c.promotion_status == "blocked" for c in candidates) == 0
