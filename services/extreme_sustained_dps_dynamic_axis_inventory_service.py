from __future__ import annotations

"""Canonical dynamic-axis inventory for generated sustained-DPS candidates.

This is a refinement prerequisite, not a DPS scorer. It inventories only dynamic
choices that already have canonical enumerators/repositories and keeps the remaining
axes explicit. In particular, static character-sheet choices are not promoted to a
proof-safe sustained-DPS upper bound without a rotation/action ceiling.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.build_candidate_armor_enchant import MODELED_ARMOR_ENCHANTS
from minmax.build_candidate_armor_trait import MODELED_ARMOR_TRAITS
from minmax.mundus_repository import MundusRepository
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from services.extreme_skill_universe_service import ExtremeSkillUniverseService
from services.extreme_sustained_dps_generated_candidate_service import (
    ExtremeSustainedDPSStructuralCandidate,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSDynamicAxisInventory:
    structural_index: int
    mundus_choices: tuple[str, ...]
    food_choices: tuple[str, ...]
    armor_trait_choices: tuple[str, ...]
    armor_enchant_choices: tuple[str, ...]
    bar_eligible_skill_ids: tuple[int, ...]
    expanded_axes: tuple[str, ...]
    deferred_axes: tuple[str, ...]
    unresolved: tuple[str, ...]
    evidence: tuple[str, ...]

    @property
    def pruning_bound_ready(self) -> bool:
        return False


class ExtremeSustainedDPSDynamicAxisInventoryService:
    """Inventory canonical refinement choices around one structural candidate."""

    EXPANDED_AXES = (
        "Mundus",
        "mapped food/drink",
        "modeled armor traits",
        "modeled CP160 Truly Superb armor enchants",
        "bar-eligible active skill identities",
    )

    DEFERRED_AXES = (
        "Ultimate/potion/execute/Heavy-Attack/encounter-demand rotation policy families",
        "runtime proc/cooldown/execute state beyond reviewed bridges",
        "proof-safe dominance/scoring across generated refinement frontiers",
        "global branch-and-bound frontier search",
        "proof-safe sustained-DPS upper bound",
    )

    def __init__(
        self,
        database_path: str | Path,
        *,
        mundus_repository: MundusRepository | None = None,
        provisioning_repository: ProvisioningStaticRepository | None = None,
        skill_universe: ExtremeSkillUniverseService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.mundus_repository = mundus_repository or MundusRepository(
            self.database_path,
            initialize=False,
        )
        self.provisioning_repository = (
            provisioning_repository
            or ProvisioningStaticRepository(self.database_path)
        )
        self.skill_universe = skill_universe or ExtremeSkillUniverseService(
            self.database_path
        )

    def inventory(
        self,
        candidate: ExtremeSustainedDPSStructuralCandidate,
    ) -> ExtremeSustainedDPSDynamicAxisInventory:
        mundus = tuple(
            sorted(
                {
                    str(name).strip()
                    for name in self.mundus_repository.list_names()
                    if str(name).strip()
                },
                key=str.casefold,
            )
        )

        foods: list[str] = []
        food_unresolved: list[str] = []
        seen_food_signatures: set[
            tuple[tuple[tuple[str, str, float, str], ...], str]
        ] = set()
        for listed in self.provisioning_repository.list_names():
            name = self.provisioning_repository.canonical_name(listed)
            if not name:
                continue
            effects, unresolved = self.provisioning_repository.resolve(name)
            if unresolved or not effects:
                if unresolved:
                    food_unresolved.extend(str(item) for item in unresolved if str(item))
                continue
            effect_signature = tuple(
                sorted(
                    (
                        str(getattr(getattr(effect, "stat", None), "value", getattr(effect, "stat", ""))),
                        str(getattr(getattr(effect, "operation", None), "value", getattr(effect, "operation", ""))),
                        float(getattr(effect, "value", 0.0)),
                        str(getattr(getattr(effect, "unit", None), "value", getattr(effect, "unit", ""))),
                    )
                    for effect in effects
                )
            )
            description_resolver = getattr(self.provisioning_repository, "description", None)
            description = (
                str(description_resolver(name) or "")
                if callable(description_resolver)
                else ""
            )
            normalized_description = " ".join(description.casefold().split())
            signature = (effect_signature, normalized_description)
            if signature in seen_food_signatures:
                continue
            seen_food_signatures.add(signature)
            foods.append(name)

        route = candidate.class_route
        base_class = getattr(getattr(route, "base_class", None), "value", None)
        if not base_class:
            base_class = str(getattr(route, "base_class", "") or "").strip()
        allowed_lines = {
            str(line or "").strip().casefold()
            for line in getattr(route, "equipped_skill_lines", ())
            if str(line or "").strip()
        }
        skill_ids: list[int] = []
        for row in self.skill_universe.actives():
            line = str(getattr(row, "skill_line", "") or "").strip().casefold()
            is_route_class_skill = (
                getattr(row, "domain", None).value == "class"
                if getattr(row, "domain", None) is not None
                else False
            )
            if is_route_class_skill and line not in allowed_lines:
                continue
            if self.skill_universe.bar_eligible(
                row,
                character_class=base_class or None,
                slot_index=0,
            ):
                skill_ids.append(int(row.skill_id))

        unresolved = tuple(
            dict.fromkeys(
                (
                    *food_unresolved,
                    "No proof-safe sustained-DPS upper bound exists yet for these static refinement axes without generated action/rotation ceilings",
                )
            )
        )
        evidence = (
            f"Structural candidate index: {int(candidate.structural_index)}",
            f"Mundus choices: {len(mundus)}",
            f"Distinct mapped static food/drink states, conservatively preserving tooltip-distinct items: {len(foods)}",
            f"Modeled armor trait choices per equipped armor slot: {len(MODELED_ARMOR_TRAITS)}",
            f"Modeled armor enchant choices per eligible armor slot: {len(MODELED_ARMOR_ENCHANTS)}",
            f"Bar-eligible active skill identities after class-route filtering: {len(set(skill_ids))}",
            "Static axis inventory does not imply a sustained-DPS ceiling; pruning remains fail-open until a proven optimistic action/rotation bound exists",
        )
        return ExtremeSustainedDPSDynamicAxisInventory(
            structural_index=int(candidate.structural_index),
            mundus_choices=mundus,
            food_choices=tuple(sorted(set(foods), key=str.casefold)),
            armor_trait_choices=tuple(MODELED_ARMOR_TRAITS),
            armor_enchant_choices=tuple(MODELED_ARMOR_ENCHANTS),
            bar_eligible_skill_ids=tuple(sorted(set(skill_ids))),
            expanded_axes=self.EXPANDED_AXES,
            deferred_axes=self.DEFERRED_AXES,
            unresolved=unresolved,
            evidence=evidence,
        )


__all__ = [
    "ExtremeSustainedDPSDynamicAxisInventory",
    "ExtremeSustainedDPSDynamicAxisInventoryService",
]
