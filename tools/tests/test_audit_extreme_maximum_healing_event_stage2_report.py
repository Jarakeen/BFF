from __future__ import annotations

from types import SimpleNamespace

from tools.audit_extreme_maximum_healing_event_stage2 import _decisive_blockers


PET = (
    "Sorcerer pet special activation requires runtime proof that the corresponding pet is summoned and alive"
)
ELDER = (
    "Blood of the Elder Dragon maximum-event scaling requires component-specific missing-Health proof for the winning recipient"
)


def test_decisive_blockers_deduplicate_repeated_route_messages_and_prioritize_search_proof():
    entries = (
        SimpleNamespace(unresolved=(PET, ELDER, "Champion Point is dynamic or not yet stat-mapped: Celerity")),
        SimpleNamespace(unresolved=(PET, ELDER, "Potion selected; activation/uptime is not part of static build state: spell power")),
    )
    omitted = (
        "whole-build optimization outside the selected Stage-2 finalist families/routes",
        "proof that a lower baseline family within an already represented source kind cannot overtake after whole-build mutation",
        "base-class change",
        "group-only buffs",
    )

    blockers = _decisive_blockers(entries, omitted)

    assert blockers == (
        ("winner legality", PET),
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
    assert all("Celerity" not in message for _, message in blockers)
    assert all("Potion selected" not in message for _, message in blockers)
