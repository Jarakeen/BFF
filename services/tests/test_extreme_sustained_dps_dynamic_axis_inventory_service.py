from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from minmax.character_progression import AttributeAllocation
from services.extreme_sustained_dps_dynamic_axis_inventory_service import (
    ExtremeSustainedDPSDynamicAxisInventoryService,
)
from services.extreme_sustained_dps_generated_candidate_service import (
    ExtremeSustainedDPSStructuralCandidate,
)


class _BaseClass(Enum):
    SORCERER = "Sorcerer"


@dataclass(frozen=True)
class _Route:
    base_class: _BaseClass = _BaseClass.SORCERER
    equipped_skill_lines: tuple[str, ...] = ("Dark Magic", "Daedric Summoning")


class _Mundus:
    def list_names(self):
        return ("The Thief", "The Lover", "The Thief", "")


@dataclass(frozen=True)
class _Effect:
    stat: str
    operation: str
    value: float
    unit: str


class _Food:
    def list_names(self):
        return ("Food A", "Food B", "Duplicate", "Unknown")

    @staticmethod
    def canonical_name(name):
        return name

    def resolve(self, name):
        if name == "Unknown":
            return (), ("unmapped food",)
        if name == "Food A":
            return (_Effect("max_magicka", "add", 1000.0, "flat"),), ()
        if name in {"Food B", "Duplicate"}:
            return (_Effect("max_stamina", "add", 1000.0, "flat"),), ()
        return (), ()


@dataclass(frozen=True)
class _Domain:
    value: str


@dataclass(frozen=True)
class _Skill:
    skill_id: int
    skill_line: str
    domain: _Domain


class _Skills:
    def actives(self):
        return (
            _Skill(1, "Dark Magic", _Domain("class")),
            _Skill(2, "Storm Calling", _Domain("class")),
            _Skill(3, "Dual Wield", _Domain("weapon")),
        )

    @staticmethod
    def bar_eligible(row, *, character_class, slot_index):
        return row.skill_id != 99


def _candidate():
    return ExtremeSustainedDPSStructuralCandidate(
        structural_index=7,
        race="Khajiit",
        class_route=_Route(),
        attributes=AttributeAllocation(health=0, magicka=64, stamina=0),
        active_bar="front",
    )


def test_inventory_expands_only_canonical_currently_supported_axes() -> None:
    service = ExtremeSustainedDPSDynamicAxisInventoryService(
        "unused.db",
        mundus_repository=_Mundus(),
        provisioning_repository=_Food(),
        skill_universe=_Skills(),
    )

    result = service.inventory(_candidate())

    assert result.structural_index == 7
    assert result.mundus_choices == ("The Lover", "The Thief")
    assert result.food_choices == ("Food A", "Food B")
    assert result.bar_eligible_skill_ids == (1, 3)
    assert result.armor_trait_choices
    assert result.armor_enchant_choices
    assert result.pruning_bound_ready is False


def test_class_skill_filter_respects_selected_route_lines() -> None:
    result = ExtremeSustainedDPSDynamicAxisInventoryService(
        "unused.db",
        mundus_repository=_Mundus(),
        provisioning_repository=_Food(),
        skill_universe=_Skills(),
    ).inventory(_candidate())

    assert 1 in result.bar_eligible_skill_ids
    assert 2 not in result.bar_eligible_skill_ids
    assert 3 in result.bar_eligible_skill_ids


def test_unmapped_food_and_missing_dps_bound_remain_explicit() -> None:
    result = ExtremeSustainedDPSDynamicAxisInventoryService(
        "unused.db",
        mundus_repository=_Mundus(),
        provisioning_repository=_Food(),
        skill_universe=_Skills(),
    ).inventory(_candidate())

    assert "unmapped food" in result.unresolved
    assert any("No proof-safe sustained-DPS upper bound" in row for row in result.unresolved)
    assert "proof-safe sustained-DPS upper bound" in result.deferred_axes
    assert any("pruning remains fail-open" in row for row in result.evidence)


class _TooltipDistinctFood(_Food):
    def list_names(self):
        return ("Food B", "Duplicate")

    @staticmethod
    def description(name):
        return {
            "Food B": "Increase Max Stamina by 1000.",
            "Duplicate": "Increase Max Stamina by 1000. Extra reviewed mechanic text.",
        }[name]


def test_tooltip_distinct_foods_with_same_static_effects_are_preserved() -> None:
    result = ExtremeSustainedDPSDynamicAxisInventoryService(
        "unused.db",
        mundus_repository=_Mundus(),
        provisioning_repository=_TooltipDistinctFood(),
        skill_universe=_Skills(),
    ).inventory(_candidate())

    assert result.food_choices == ("Duplicate", "Food B")
    assert any("tooltip-distinct" in row for row in result.evidence)
