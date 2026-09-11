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


def test_poxito_projection_has_saw_armor_totem_and_berserker_handling():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get("poxito", "Poxito")

    assert "Main Phase" in _labels(projection)
    strategy = _strategy(projection)
    assert "Bone Armor" in strategy
    assert "saw" in strategy["Bone Armor"].mitigation.casefold()
    assert "Soul Storm" in strategy
    assert "totem" in strategy["Soul Storm"].mitigation.casefold()
    assert "Skeletal Berserker" in strategy
    assert "taunt" in strategy["Skeletal Berserker"].mitigation.casefold()


def test_voskrona_projection_has_death_essence_thresholds_and_fatal_pool_control():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "voskrona_stonehulk_poxito", "Voskrona Stonehulk Poxito"
    )

    assert {"Main Boss Phase", "Death Essence I", "Death Essence II", "Execute / Overlap"} <= _labels(projection)
    assert {"75%", "50%", "30%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Fatal Pool" in strategy
    assert "invulnerable" in strategy["Fatal Pool"].mitigation.casefold()
    assert "Pulsing Ring" in strategy
    assert "block" in strategy["Pulsing Ring"].mitigation.casefold()
    assert "Sentinel Tether" in strategy


def test_talen_lah_projection_preserves_alternating_boss_flow_and_guardian_assignments():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "talen_lah", "Talen-Lah and Bar-Sakka"
    )

    assert {"Talen-Lah Opening", "Bar-Sakka Phase I", "Talen-Lah Return", "Bar-Sakka Phase II", "Final Talen-Lah"} <= _labels(projection)
    assert {"80%", "50%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Guardian Circles" in strategy
    assert "one player" in strategy["Guardian Circles"].mitigation.casefold()
    assert "Seeping Viscera" in strategy
    assert "edge" in strategy["Seeping Viscera"].mitigation.casefold()
    assert "Vortex" in strategy


def test_saldezaar_projection_has_hardmode_ruptures_and_splinter_cleanses():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "quarrymaster_saldezaar", "Quarrymaster Saldezaar"
    )

    assert {"Main Phase", "Rupture I", "Rupture II"} <= _labels(projection)
    assert {"65% (Hard Mode)", "30% (Hard Mode)"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Seismic Splinters" in strategy
    assert "cleanse" in strategy["Seismic Splinters"].mitigation.casefold()
    assert "Galvanizing Imp" in strategy
    assert "priority" in strategy["Galvanizing Imp"].mitigation.casefold()


def test_black_gem_monstrosity_projection_has_lava_thresholds_and_healer_beam_bait():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "black_gem_monstrosity", "Black Gem Monstrosity"
    )

    assert {"Main Phase", "Lava Phase I", "Lava Phase II", "Execute / Heating Pattern"} <= _labels(projection)
    assert {"80%", "50%", "35%"} <= _markers(projection)
    strategy = _strategy(projection)
    assert "Lapidating Bash" in strategy
    assert "edge" in strategy["Lapidating Bash"].mitigation.casefold()
    assert "Soul Focus" in strategy
    assert "healer" in strategy["Soul Focus"].mitigation.casefold()
    assert "Black Gem Shards" in strategy


def test_vykand_projection_has_color_puzzle_enervation_and_vision_calls():
    projection = EncounterGuideEvidenceProjectionService(DATA_ROOT).get(
        "high_soulbinder_vykand", "High Soulbinder Vykand"
    )

    assert {"Main Puzzle Phase", "Ominous Vision / Annihilation"} <= _labels(projection)
    assert "60% and recurring" in _markers(projection)
    strategy = _strategy(projection)
    assert "Refraction Color Puzzle" in strategy
    assert "third color" in strategy["Refraction Color Puzzle"].mitigation.casefold()
    assert "Acute Enervation" in strategy
    assert "second target" in strategy["Acute Enervation"].mitigation.casefold()
    assert "Soulbinding Slam" in strategy
