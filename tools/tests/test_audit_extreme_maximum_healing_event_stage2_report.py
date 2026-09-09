from __future__ import annotations

from types import SimpleNamespace

from services.extreme_maximum_heal_unresolved_relevance_service import (
    ExtremeMaximumHealUnresolvedRelevanceService,
)
from tools.audit_extreme_maximum_healing_event_stage2 import (
    _decisive_blockers,
    _setup_prerequisites,
)


PET = (
    "Sorcerer pet special activation requires runtime proof that the corresponding pet is summoned and alive"
)
POTION = "Potion selected; activation/uptime is not part of static build state: spell power"
ELDER = (
    "Blood of the Elder Dragon maximum-event scaling requires component-specific missing-Health proof for the winning recipient"
)


def _entries():
    return (
        SimpleNamespace(unresolved=(PET, ELDER, "Champion Point is dynamic or not yet stat-mapped: Celerity")),
        SimpleNamespace(unresolved=(PET, ELDER, POTION)),
    )


def test_decisive_blockers_exclude_achievable_setup_and_prioritize_search_proof():
    omitted = (
        "whole-build optimization outside the selected Stage-2 finalist families/routes",
        "proof that a lower baseline family within an already represented source kind cannot overtake after whole-build mutation",
        "base-class change",
        "group-only buffs",
    )

    blockers = _decisive_blockers(_entries(), omitted)

    assert blockers == (
        ("winner magnitude", ELDER),
        (
            "search proof",
            "proof that a lower baseline family within an already represented source kind cannot overtake after whole-build mutation",
        ),
        (
            "search proof",
            "whole-build optimization outside the selected Stage-2 finalist families/routes",
        ),
        ("search proof", "base-class change"),
    )
    assert all(PET not in message for _, message in blockers)
    assert all("Celerity" not in message for _, message in blockers)
    assert all("Potion selected" not in message for _, message in blockers)


def test_stage2_setup_prerequisites_deduplicate_across_routes():
    relevance = ExtremeMaximumHealUnresolvedRelevanceService()

    assert _setup_prerequisites(_entries(), relevance) == (PET, POTION)
