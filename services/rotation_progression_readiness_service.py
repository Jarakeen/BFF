from __future__ import annotations

from dataclasses import dataclass

from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class RotationProgressionReadiness:
    """Read-only evidence about whether canonical progression can drive costs."""

    character_id: str
    resource: ResourceType
    canonical_owned_skill_lines: tuple[str, ...]
    equipped_armor_skill_lines: tuple[str, ...]
    cost_relevant_skill_lines: tuple[str, ...]
    missing_cost_relevant_skill_lines: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return bool(self.character_id) and not self.unresolved and not self.missing_cost_relevant_skill_lines


class RotationProgressionReadinessService:
    """Check canonical progression without inferring ownership from equipment.

    Equipped armor is evidence about which armor passives may affect the current
    build's action costs. It is never promoted to character-owned progression by
    this service. Missing canonical ownership remains explicit for the caller to
    resolve through the character progression workflow.
    """

    def __init__(self, adapter: MinmaxCharacterProgressionAdapter) -> None:
        self.adapter = adapter

    def assess(
        self,
        *,
        build: PlayerBuild,
        resource: ResourceType = ResourceType.MAGICKA,
    ) -> RotationProgressionReadiness:
        resolution = self.adapter.resolve(build)
        owned = tuple(resolution.progression.owned_skill_lines)
        equipped = self._equipped_armor_skill_lines(build)
        relevant = self._cost_relevant_skill_lines(equipped, resource)
        owned_keys = {value.casefold() for value in owned}
        missing = tuple(value for value in relevant if value.casefold() not in owned_keys)

        unresolved = list(resolution.unresolved)
        if not owned:
            unresolved.append("Canonical character progression has no owned skill lines recorded")

        return RotationProgressionReadiness(
            character_id=resolution.character_id,
            resource=resource,
            canonical_owned_skill_lines=owned,
            equipped_armor_skill_lines=equipped,
            cost_relevant_skill_lines=relevant,
            missing_cost_relevant_skill_lines=missing,
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _equipped_armor_skill_lines(build: PlayerBuild) -> tuple[str, ...]:
        lines = {
            f"{str(entry.get('Weight', '') or '').strip().title()} Armor"
            for entry in build.Armor.values()
            if str(entry.get("Weight", "") or "").strip().casefold()
            in {"light", "medium", "heavy"}
        }
        return tuple(sorted(lines))

    @staticmethod
    def _cost_relevant_skill_lines(
        equipped: tuple[str, ...],
        resource: ResourceType,
    ) -> tuple[str, ...]:
        equipped_keys = {value.casefold() for value in equipped}
        relevant: list[str] = []
        if resource is ResourceType.MAGICKA and "light armor" in equipped_keys:
            relevant.append("Light Armor")
        if resource is ResourceType.STAMINA and "medium armor" in equipped_keys:
            relevant.append("Medium Armor")
        return tuple(relevant)

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)
