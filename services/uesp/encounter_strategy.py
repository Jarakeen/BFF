from __future__ import annotations

"""Curated encounter mechanics and raid strategies.

This is intentionally separate from UESP parsing. UESP supplies source facts;
this module records verified/local raid interpretation without presenting it as
an immutable game rule.
"""

from dataclasses import dataclass

from models.uesp_models import UespBoss


@dataclass(frozen=True)
class MechanicStrategySpec:
    name: str
    ability_name: str
    mechanic_type: str
    damage_type: str | None = None
    target_count: int | None = None
    requires_movement: bool | None = None
    requires_positioning: bool | None = None
    requires_cleanse: bool | None = None
    persistent_hazard: bool | None = None
    failure_is_fatal: bool | None = None
    interruptible: bool | None = None
    interrupt_note: str = ""
    strategy: str = ""
    recommended_role: str | None = None
    priority: str | None = None
    rationale: str = ""


# First curated encounter: Oaxiltso in Rockgrove.
# These are raid-strategy annotations, not claims that UESP itself prescribes
# the strategy. The source ability descriptions still come from the parser.
OAXILTSO_MECHANICS = (
    MechanicStrategySpec(
        name="Noxious Sludge",
        ability_name="Noxious Sludge",
        mechanic_type="targeted_hazard",
        damage_type="poison",
        target_count=2,
        requires_movement=True,
        requires_positioning=True,
        requires_cleanse=True,
        persistent_hazard=True,
        interruptible=False,
        interrupt_note="Not interruptible.",
        strategy="Healers kite the spit.",
        recommended_role="Healer",
        priority="high",
        rationale=(
            "The UESP ability description says the two targets are prioritized "
            "from those farthest from the corner pools. The established raid "
            "strategy is for healers to kite the spit."
        ),
    ),
    MechanicStrategySpec(
        name="Savage Blitz",
        ability_name="Savage Blitz",
        mechanic_type="charge",
        damage_type="physical",
        requires_movement=True,
        requires_positioning=True,
        interruptible=True,
        interrupt_note="Interruptible; do not confuse with Noxious Sludge.",
        strategy="Interrupt the Blitz and avoid its path.",
        recommended_role="All",
        priority="high",
        rationale="The charge is a major execution check and is the interruptible Oaxiltso attack.",
    ),
    MechanicStrategySpec(
        name="Fiery Stomp",
        ability_name="Fiery Stomp",
        mechanic_type="area_attack",
        damage_type="flame",
        requires_movement=True,
        requires_positioning=True,
        interruptible=False,
        interrupt_note="Not interruptible.",
        strategy="Respect the flaming trails and maintain safe positioning.",
        recommended_role="All",
        priority="high",
        rationale="Three stomps release outward flame trails without an AoE indicator.",
    ),
)


def curated_mechanics_for(boss: UespBoss) -> tuple[MechanicStrategySpec, ...]:
    if boss.id == "oaxiltso" and boss.content_id == "rockgrove":
        return OAXILTSO_MECHANICS
    return ()
