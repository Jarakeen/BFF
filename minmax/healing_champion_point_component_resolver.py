from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .champion_point_skill_repository import ChampionPointSkillRepository
from .champion_point_static_repository import (
    CHAMPION_SKILL_TYPE_NORMAL_SLOTTABLE,
    ChampionPointStaticRepository,
)
from .character_build.champion_points import ChampionPointAllocation
from .skill_component_actual_effect_modifiers import SkillComponentActualEffectModifier
from .skill_component_classification import SkillEffectKind
from .skill_component_repository import SkillComponentRepository


_COLOR = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
_THRESHOLDS = (10, 20, 30, 40, 50)
_EXPECTED_JUMPS = (0,) + _THRESHOLDS


@dataclass(frozen=True)
class HealingChampionPointComponentModifiers:
    """Actual-effect modifiers for one classified healing coefficient.

    ``power_bonus`` is added inside the coefficient's Weapon/Spell Damage power
    term. ``healing_done_percent`` is a single additive category bucket applied
    after raw coefficient evaluation. Neither value is a standing sheet stat or
    assumed tooltip-visible modifier.
    """

    power_bonus: float = 0.0
    healing_done_percent: float = 0.0
    applied: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class _VerifiedHealingCP:
    name: str
    per_stage: float
    description_fragment: str
    contribution: str


_VERIFIED = {
    "rejuvenator": _VerifiedHealingCP(
        name="Rejuvenator",
        per_stage=41.0,
        description_fragment="Grants 41 Weapon and Spell Damage to your healing abilities per stage.",
        contribution="power",
    ),
    "soothing tide": _VerifiedHealingCP(
        name="Soothing Tide",
        per_stage=2.0,
        description_fragment="Increases your Healing Done by area of effect heals by 2% per stage.",
        contribution="aoe_healing_done",
    ),
    "swift renewal": _VerifiedHealingCP(
        name="Swift Renewal",
        per_stage=2.0,
        description_fragment="Increases your Healing Done with healing over time effects by 2% per stage.",
        contribution="hot_healing_done",
    ),
}


class HealingChampionPointComponentResolver:
    """Resolve personal healing CP math at coefficient-component scope.

    Applicability is intentionally two-stage and fail-closed:
      1. ESO-Hub's harvested CP -> rank/morph relationship must exist.
      2. Persisted Phase 3 component semantics must qualify the coefficient.

    Component semantics may narrow an explicit relationship but never invent
    one. Source CP metadata is also verified against the current database before
    any numeric contribution is returned.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        relationship_repository: ChampionPointSkillRepository | None = None,
        component_repository: SkillComponentRepository | None = None,
        cp_repository: ChampionPointStaticRepository | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.relationships = relationship_repository or ChampionPointSkillRepository(
            database_path
        )
        self.components = component_repository or SkillComponentRepository(database_path)
        self.cp = cp_repository or ChampionPointStaticRepository(database_path)

    @staticmethod
    def _key(value: object) -> str:
        text = str(value or "").strip().casefold().replace("_", " ").replace("-", " ")
        return " ".join(text.split())

    @staticmethod
    def _clean_description(value: str) -> str:
        return " ".join(_COLOR.sub("", str(value or "")).split())

    @staticmethod
    def _stages(points: int, max_points: int) -> int:
        allocated = max(0, min(int(points), int(max_points)))
        return sum(1 for threshold in _THRESHOLDS if allocated >= threshold)

    @staticmethod
    def _condition_satisfied(condition: str | None, *, is_slotted: bool) -> bool:
        key = " ".join(str(condition or "").strip().casefold().split())
        if not key:
            return True
        if key == "only while slotted":
            return bool(is_slotted)
        return False

    def _allocations(
        self,
        allocations: Iterable[ChampionPointAllocation],
    ) -> dict[str, ChampionPointAllocation]:
        result: dict[str, ChampionPointAllocation] = {}
        for allocation in allocations:
            key = self._key(allocation.node_id)
            if key in _VERIFIED:
                result[key] = allocation
        return result

    def _verify_source(self, rule: _VerifiedHealingCP) -> tuple[int | None, str | None]:
        record = self.cp.get(rule.name)
        if record is None:
            return None, f"Healing Champion Point not found: {rule.name}"

        description = self._clean_description(record.description)
        if (
            record.skill_type != CHAMPION_SKILL_TYPE_NORMAL_SLOTTABLE
            or record.max_points != 50
            or tuple(record.jump_points) != _EXPECTED_JUMPS
            or rule.description_fragment.casefold() not in description.casefold()
        ):
            return None, (
                "Healing Champion Point source no longer matches verified mapping: "
                f"{rule.name}"
            )
        return record.max_points, None

    def resolve(
        self,
        *,
        allocations: Iterable[ChampionPointAllocation],
        skill_rank_id: int,
        coefficient_number: int,
        is_slotted: bool,
    ) -> HealingChampionPointComponentModifiers:
        component = self.components.get_component(skill_rank_id, coefficient_number)
        if component is None:
            return HealingChampionPointComponentModifiers(
                unresolved=(
                    f"Skill component classification unavailable: skill_rank_id={int(skill_rank_id)} "
                    f"coefficient={int(coefficient_number)}",
                )
            )
        if component.effect_kind is not SkillEffectKind.HEAL:
            return HealingChampionPointComponentModifiers()

        selected = self._allocations(allocations)
        relationships = {
            self._key(row.champion_point_name): row
            for row in self.relationships.get_for_skill_rank(skill_rank_id)
            if self._key(row.champion_point_name) in _VERIFIED
        }

        power_bonus = 0.0
        healing_done = 0.0
        applied: list[str] = []
        unresolved: list[str] = []

        for key in ("rejuvenator", "swift renewal", "soothing tide"):
            allocation = selected.get(key)
            relationship = relationships.get(key)
            if allocation is None or allocation.points <= 0 or relationship is None:
                continue

            rule = _VERIFIED[key]
            if not self._condition_satisfied(relationship.condition, is_slotted=is_slotted):
                if relationship.condition and self._key(relationship.condition) != "only while slotted":
                    unresolved.append(
                        f"Unsupported healing CP relationship condition: {rule.name}: {relationship.condition}"
                    )
                continue

            if rule.contribution == "hot_healing_done":
                if component.is_dot is None:
                    unresolved.append(
                        f"Healing CP applicability unresolved: {rule.name}: component periodicity unknown"
                    )
                    continue
                if component.is_dot is not True:
                    continue
            elif rule.contribution == "aoe_healing_done":
                if component.is_aoe is None:
                    unresolved.append(
                        f"Healing CP applicability unresolved: {rule.name}: component target shape unknown"
                    )
                    continue
                if component.is_aoe is not True:
                    continue

            max_points, source_error = self._verify_source(rule)
            if source_error is not None or max_points is None:
                unresolved.append(source_error or f"Healing Champion Point source unresolved: {rule.name}")
                continue

            stages = self._stages(allocation.points, max_points)
            if stages <= 0:
                continue
            amount = rule.per_stage * stages
            if rule.contribution == "power":
                power_bonus += amount
            else:
                healing_done += amount
            applied.append(rule.name)

        return HealingChampionPointComponentModifiers(
            power_bonus=power_bonus,
            healing_done_percent=healing_done,
            applied=tuple(applied),
            unresolved=tuple(unresolved),
        )

    def resolve_for_skill(
        self,
        *,
        allocations: Iterable[ChampionPointAllocation],
        skill_rank_id: int,
        coefficient_numbers: Iterable[int],
        is_slotted: bool,
    ) -> tuple[tuple[SkillComponentActualEffectModifier, ...], tuple[str, ...]]:
        """Bridge verified CP rules to the generic tooltip calculator input."""

        stable_allocations = tuple(allocations)
        modifiers: list[SkillComponentActualEffectModifier] = []
        unresolved: list[str] = []
        for coefficient_number in coefficient_numbers:
            resolved = self.resolve(
                allocations=stable_allocations,
                skill_rank_id=skill_rank_id,
                coefficient_number=int(coefficient_number),
                is_slotted=is_slotted,
            )
            unresolved.extend(resolved.unresolved)
            if not resolved.applied:
                continue
            modifiers.append(
                SkillComponentActualEffectModifier(
                    coefficient_number=int(coefficient_number),
                    power_bonus=resolved.power_bonus,
                    additive_percent=resolved.healing_done_percent,
                    sources=resolved.applied,
                )
            )
        return tuple(modifiers), tuple(unresolved)
