from pathlib import Path

from services.encounter_guide_evidence_projection_service import (
    EncounterGuideEvidenceProjectionService,
)


DATA_ROOT = Path("data")


def _labels(projection):
    return {row.label for row in projection.timeline}


def _markers(projection):
    return {row.marker for row in projection.timeline}


def _strategy(projection):
    return {row.mechanic: row for row in projection.strategy}


def test_mantikora_projection_has_portal_popcorn_stomp_and_shard_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "possessed_mantikora", "Possessed Mantikora"
    )

    assert {"Main Phase", "Celestial Nightmare Portal"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "Popcorn" in strategy
    assert "backward" in strategy["Popcorn"].mitigation.casefold()
    assert "Stomp" in strategy
    assert "block" in strategy["Stomp"].mitigation.casefold()
    assert "Shards" in strategy
    assert "furthest" in strategy["Shards"].summary.casefold()


def test_stonebreaker_projection_has_enrage_overcharger_thresholds_and_poison_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "stonebreaker", "Stonebreaker"
    )

    assert {"Main Phase", "Enrage", "Overcharger Waves"} <= _labels(projection)
    assert {"75%", "50%", "25%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Ground Pound" in strategy
    assert "blocks" in strategy["Ground Pound"].mitigation.casefold()
    assert "Poison Ball" in strategy
    assert "spreads" in strategy["Poison Ball"].mitigation.casefold()


def test_ozara_projection_has_overcharger_totem_and_pin_rescue_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "ozara", "Ozara"
    )

    assert "Main Phase" in _labels(projection)
    strategy = _strategy(projection)
    assert "Overcharger Priority" in strategy
    assert "Shaman Totem" in strategy
    assert "Kill the totem, not the Shaman" in strategy["Shaman Totem"].mitigation
    assert "Trapping Bolt" in strategy
    assert "synergy" in strategy["Trapping Bolt"].mitigation.casefold()


def test_serpent_projection_has_poison_cycle_bubbles_and_hardmode_world_shaper():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "the_serpent_celestial", "The Serpent"
    )

    assert {"Main Phase", "Poison Phase", "Orb / Bubble Phase"} <= _labels(projection)
    strategy = _strategy(projection)
    assert "World Shaper" in strategy
    assert "leaves the boss's hand" in strategy["World Shaper"].mitigation
    assert "Mantikora Adds" in strategy
    assert "poison phases 2 and 4" in strategy["Mantikora Adds"].mitigation
    assert "Magicka Bomb" in strategy
    assert "0-10%" in strategy["Magicka Bomb"].mitigation
