from __future__ import annotations

from services.extreme_maximum_heal_unresolved_relevance_service import (
    ExtremeMaximumHealUnresolvedRelevanceService,
)


def test_maximum_heal_relevance_downgrades_only_proven_ambient_diagnostics():
    result = ExtremeMaximumHealUnresolvedRelevanceService().classify(
        (
            "Champion Point is dynamic or not yet stat-mapped: Master Gatherer",
            "Champion Point is dynamic or not yet stat-mapped: Celerity",
            "The Steed: movement_speed unresolved (Movement speed is outside the current character-sheet stat layer.)",
            "Front Bar Training: non-combat experience trait",
            "Front Bar Charged: requires status-effect chance model",
            "Front Bar Decisive: requires Ultimate generation model",
            "Potion selected; activation/uptime is not part of static build state: spell power",
            "Sorcerer pet special activation requires runtime proof that the corresponding pet is summoned and alive",
        )
    )

    assert result.ambient == (
        "Champion Point is dynamic or not yet stat-mapped: Master Gatherer",
        "Champion Point is dynamic or not yet stat-mapped: Celerity",
        "The Steed: movement_speed unresolved (Movement speed is outside the current character-sheet stat layer.)",
        "Front Bar Training: non-combat experience trait",
        "Front Bar Charged: requires status-effect chance model",
        "Front Bar Decisive: requires Ultimate generation model",
    )
    assert result.relevant == (
        "Potion selected; activation/uptime is not part of static build state: spell power",
        "Sorcerer pet special activation requires runtime proof that the corresponding pet is summoned and alive",
    )
    assert not result.objective_complete
