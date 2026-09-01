from __future__ import annotations

from pathlib import Path

from services.encounter_evidence import reconcile_encounter_evidence
from services.encounter_promotion import build_encounter_promotion_preview
from tools.reconcile_encounter_evidence import _load_packet


PACKET = Path("data/encounter_evidence/rockgrove_boss2.json")


def test_bahsei_packet_preserves_corroborated_core_mechanics():
    payload, evidence = _load_packet(PACKET)
    facts = reconcile_encounter_evidence(evidence)
    candidates = build_encounter_promotion_preview(facts)

    assert payload["content_id"] == "rockgrove"
    assert payload["encounter_id"] == "flame_herald_bahsei"
    assert len(facts) == 25

    by_ref = {
        f"{candidate.fact.fact_type}:{candidate.fact.fact_key}": candidate
        for candidate in candidates
    }

    eligible_refs = {
        "mechanic_state:skull_salvo_exists",
        "mechanic_detail:skull_salvo_interruptible",
        "mechanic_state:cursed_ground_exists",
        "mechanic_detail:cursed_ground_targeting",
        "mechanic_state:death_touch_exists",
        "mechanic_detail:death_touch_spread_behavior",
        "mechanic_state:sickle_strike_exists",
        "mechanic_state:flesh_abomination_summons_exist",
        "transition:flesh_abomination_spawn_thresholds",
        "mechanic_state:fire_behemoth_summons_exist",
        "mechanic_detail:fire_behemoth_begins_at_50_percent",
        "mechanic_state:hardmode_creeping_eye_exists",
    }
    for ref in eligible_refs:
        assert by_ref[ref].promotion_status == "eligible"

    thresholds = by_ref["transition:flesh_abomination_spawn_thresholds"].fact
    assert thresholds.value == {
        "thresholds": ["90%", "85%", "80%", "75%", "70%", "65%", "60%"]
    }
    assert thresholds.status == "corroborated"

    eye = by_ref["mechanic_state:hardmode_creeping_eye_exists"].fact
    assert eye.status == "corroborated"

    assert by_ref["transition:fire_behemoth_spawn_thresholds_uesp"].promotion_status == "review_required"
    assert by_ref["transition:meteor_swarm_phase_thresholds_uesp"].promotion_status == "review_required"

    assert sum(c.promotion_status == "eligible" for c in candidates) == 12
    assert sum(c.promotion_status == "review_required" for c in candidates) == 13
    assert sum(c.promotion_status == "blocked" for c in candidates) == 0
