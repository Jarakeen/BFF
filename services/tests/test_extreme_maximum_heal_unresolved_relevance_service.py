from __future__ import annotations

from services.extreme_maximum_heal_unresolved_relevance_service import (
    ExtremeMaximumHealUnresolvedRelevanceService,
)


PET = (
    "Sorcerer pet special activation requires runtime proof that the corresponding pet is summoned and alive"
)


def test_maximum_heal_relevance_separates_blockers_setup_and_ambient_diagnostics():
    result = ExtremeMaximumHealUnresolvedRelevanceService().classify(
        (
            "Champion Point is dynamic or not yet stat-mapped: Master Gatherer",
            "Champion Point is dynamic or not yet stat-mapped: Celerity",
            "The Steed: movement_speed unresolved (Movement speed is outside the current character-sheet stat layer.)",
            "Front Bar Training: non-combat experience trait",
            "Front Bar Charged: requires status-effect chance model",
            "Front Bar Decisive: requires Ultimate generation model",
            "Potion selected; activation/uptime is not part of static build state: spell power",
            PET,
        )
    )

    assert result.ambient == (
        "Champion Point is dynamic or not yet stat-mapped: Master Gatherer",
        "Champion Point is dynamic or not yet stat-mapped: Celerity",
        "The Steed: movement_speed unresolved (Movement speed is outside the current character-sheet stat layer.)",
        "Front Bar Training: non-combat experience trait",
    )
    assert result.setup_prerequisites == (PET,)
    assert result.relevant == (
        "Front Bar Charged: requires status-effect chance model",
        "Front Bar Decisive: requires Ultimate generation model",
        "Potion selected; activation/uptime is not part of static build state: spell power",
    )
    assert not result.objective_complete


def test_setup_prerequisite_alone_does_not_block_achievable_maximum_proof():
    result = ExtremeMaximumHealUnresolvedRelevanceService().classify((PET,))

    assert result.relevant == ()
    assert result.setup_prerequisites == (PET,)
    assert result.ambient == ()
    assert result.objective_complete
