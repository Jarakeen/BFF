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
        rationale="The established raid strategy is for healers to kite the spit.",
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
        rationale="The charge is a major execution check and the interruptible Oaxiltso attack.",
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


BAHSEI_MECHANICS = (
    MechanicStrategySpec(
        name="Bahsei's Salvo",
        ability_name="Skull Salvo",
        mechanic_type="interrupt",
        damage_type="flame",
        interruptible=True,
        interrupt_note="Verified interrupt mechanic; UESP ability is named Skull Salvo.",
        strategy="Interrupt the Salvo before the channel completes.",
        recommended_role="Tank / assigned interrupter",
        priority="high",
        rationale="Raid-helper sources identify Bahsei's Salvo as an interrupt alert.",
    ),
    MechanicStrategySpec(
        name="Death Touch",
        ability_name="Death Touch/Kiss of Death",
        mechanic_type="spread",
        damage_type="frost",
        target_count=2,
        requires_movement=True,
        requires_positioning=True,
        failure_is_fatal=True,
        interruptible=False,
        interrupt_note="Not an interrupt mechanic.",
        strategy="Cursed players move away from the group and allow the curse to resolve without catching other players.",
        recommended_role="All",
        priority="critical",
        rationale="External encounter sources describe two cursed players and directional AoEs that can spread the curse.",
    ),
    MechanicStrategySpec(
        name="Cursed Ground",
        ability_name="Cursed Ground/Unholy Spike",
        mechanic_type="hazard",
        damage_type="flame",
        requires_movement=True,
        requires_positioning=True,
        persistent_hazard=True,
        interruptible=False,
        strategy="Keep the ground hazards controlled and avoid placing them where they compromise the group's safe space.",
        recommended_role="All",
        priority="high",
        rationale="Cursed Ground is a recurring ground/chain hazard.",
    ),
    MechanicStrategySpec(
        name="Sickle Strike",
        ability_name="Sickle Strike",
        mechanic_type="area_attack",
        damage_type="flame",
        requires_movement=True,
        requires_positioning=True,
        interruptible=False,
        strategy="Recognize the three outgoing AoEs and move through safe space without breaking the group formation unnecessarily.",
        recommended_role="All",
        priority="medium",
        rationale="Sickle Strike is described as three outgoing AoEs from Bahsei.",
    ),
    MechanicStrategySpec(
        name="Behemoth Spawn",
        ability_name="Summon Behemoth",
        mechanic_type="add_spawn",
        damage_type="flame",
        requires_positioning=True,
        interruptible=False,
        strategy="Prioritize the Behemoth over boss damage and control its position.",
        recommended_role="DD / Tank",
        priority="high",
        rationale="Behemoths are a priority add during the later portion of the fight.",
    ),
    MechanicStrategySpec(
        name="Specter Spawn",
        ability_name="Summon Specters",
        mechanic_type="add_spawn",
        requires_movement=True,
        interruptible=False,
        strategy="Kill the Specters promptly while maintaining group positioning.",
        recommended_role="DD",
        priority="medium",
        rationale="Specters add pressure during the lower-health portion of Bahsei.",
    ),
)


def curated_mechanics_for(boss: UespBoss) -> tuple[MechanicStrategySpec, ...]:
    if boss.id == "oaxiltso" and boss.content_id == "rockgrove":
        return OAXILTSO_MECHANICS
    if boss.id == "flame_herald_bahsei" and boss.content_id == "rockgrove":
        return BAHSEI_MECHANICS
    return ()
