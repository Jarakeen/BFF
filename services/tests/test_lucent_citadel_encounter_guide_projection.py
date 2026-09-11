from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


DATA_ROOT = Path("data")


def _markers(projection):
    return {row.marker for row in projection.timeline}


def _labels(projection):
    return {row.label for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_ryelaz_zilyesset_projection_has_swap_cycle_and_synchronized_kill():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "ryelaz_zilyesset", "Count Ryelaz and Zilyesset"
    )

    assert {"Pull", "~60s", "First boss death"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Annihilation" in strategy
    assert "glowing platform" in strategy["Annihilation"].mitigation
    assert "Rejuvenation" in strategy
    assert "10 seconds" in strategy["Rejuvenation"].mitigation


def test_orphic_projection_has_color_change_thresholds_and_fate_pillar_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "orphic_shattered_shard", "Orphic Shattered Shard"
    )

    assert {"90%", "60%", "40%", "25%", "15%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Color Change" in strategy
    assert "mirror" in strategy["Color Change"].mitigation.casefold()
    assert "Shockwave" in strategy
    assert "Fate Pillar" in strategy["Shockwave"].mitigation
    assert "Shard Volley" in strategy
    assert "damage type: magic" in strategy["Shard Volley"].summary.casefold()


def test_xoryn_projection_is_timer_driven_and_has_tank_current_mirror_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "xoryn", "Xoryn"
    )

    assert {"Xoryn / Arcane Knot", "Fluctuating Current", "Tempest Assault / Mirrors"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Accelerating Charge" in strategy
    assert "Tank swap" in strategy["Accelerating Charge"].mitigation
    assert "Fluctuating Current" in strategy
    assert "10–15 seconds" in strategy["Fluctuating Current"].mitigation
    assert "Tempest Assault" in strategy
    assert "all 12 players" in strategy["Tempest Assault"].mitigation
    assert "Arcane Knot Fracture" in strategy
    assert "Hard Mode" in strategy["Arcane Knot Fracture"].mitigation
