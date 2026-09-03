from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.effect_instance import EffectVariant
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from models.build_model import PlayerBuild
from services.build_service import BuildService
from services.character_progression_service import CharacterProgressionService
from services.potion_effect_repository import PotionEffectRepository
from services.skill_effect_repository import SkillEffectRepository
from services.gear_effect_repository import GearEffectRepository


@dataclass(frozen=True)
class SavedBuildCapabilityAudit:
    character_name: str
    build_name: str
    character_id: str | None
    resolved_sources: tuple[str, ...]
    resolved_effects: tuple[EffectVariant, ...]
    conditional_sources: tuple[str, ...]
    unresolved: tuple[str, ...]
    capability_unresolved: tuple[str, ...]
    boundaries: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return not self.capability_unresolved


class SavedBuildCapabilityService:
    """Resolve what a saved build can provide without pretending runtime uptime exists."""

    _INTENTIONAL_STATIC_BOUNDARY_PREFIXES = (
        "Potion selected; activation/uptime is not part of static build state:",
    )

    def __init__(
        self,
        builds: BuildService,
        database_path: Path,
        *,
        context_factory=None,
        progression=None,
        skills=None,
        gear=None,
        potions=None,
    ) -> None:
        self.builds = builds
        database_path = Path(database_path)
        self.context_factory = context_factory or Phase5BuildCalculationContextFactory(database_path)
        self.progression = progression or CharacterProgressionService(database_path)
        self.skills = skills or SkillEffectRepository(database_path)
        self.gear = gear or GearEffectRepository(database_path)
        self.potions = potions or PotionEffectRepository(database_path)

    @staticmethod
    def _clean(value) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _active_set_counts(build: PlayerBuild, active_bar: str) -> dict[str, int]:
        counts: dict[str, int] = {}

        def add(name: str, pieces: int = 1) -> None:
            name = SavedBuildCapabilityService._clean(name)
            if name:
                counts[name] = counts.get(name, 0) + pieces

        for slot in ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet"):
            add(build.Armor.get(slot, {}).get("Set", ""))
        add(build.Necklace.Set)
        add(build.Ring1.Set)
        add(build.Ring2.Set)

        weapon = build.FrontBarWeapon if active_bar == "front" else build.BackBarWeapon
        pieces = 2 if "staff" in SavedBuildCapabilityService._clean(weapon.WeaponType).casefold() else 1
        add(weapon.Set, pieces)
        return counts

    @classmethod
    def _partition_context_messages(cls, messages) -> tuple[list[str], list[str]]:
        unresolved: list[str] = []
        boundaries: list[str] = []
        for message in messages:
            text = str(message)
            if any(text.startswith(prefix) for prefix in cls._INTENTIONAL_STATIC_BOUNDARY_PREFIXES):
                boundaries.append(text)
            else:
                unresolved.append(text)
        return unresolved, boundaries

    @classmethod
    def _partition_context_messages_with_cp(cls, messages) -> tuple[list[str], list[str]]:
        unresolved, boundaries = cls._partition_context_messages(messages)
        kept: list[str] = []
        for text in unresolved:
            if text.startswith("Champion Point star ") and "does not resolve to a canonical effect" in text:
                boundaries.append(text)
            else:
                kept.append(text)
        return kept, boundaries

    def _skill_variants(self, build: PlayerBuild, active_bar: str, unresolved: list[str]) -> list[EffectVariant]:
        names = build.FrontBarSkills if active_bar == "front" else build.BackBarSkills
        variants: list[EffectVariant] = []
        for name in names:
            name = self._clean(name)
            if not name:
                continue
            resolved = self.skills.resolve(name)
            unresolved.extend(resolved.unresolved)
            variants.extend(resolved.effects)
        return variants

    def _gear_variants(self, build: PlayerBuild, active_bar: str, unresolved: list[str]) -> list[EffectVariant]:
        variants: list[EffectVariant] = []
        for set_name, pieces in self._active_set_counts(build, active_bar).items():
            resolved = self.gear.resolve(set_name, active_pieces=pieces)
            unresolved.extend(resolved.unresolved)
            variants.extend(resolved.effects)
        return variants

    def audit_build(self, build: PlayerBuild) -> SavedBuildCapabilityAudit:
        unresolved: list[str] = []
        capability_unresolved: list[str] = []
        boundaries: list[str] = []
        sources: list[str] = []
        effects: list[EffectVariant] = []

        progression = self.progression.resolve(build)
        unresolved.extend(progression.unresolved)

        for active_bar in ("front", "back"):
            try:
                context = self.context_factory.build(
                    character_id=progression.character_id or "unresolved-character",
                    build_id=self._clean(getattr(build, "BuildId", "")) or build.BuildName or "saved-build",
                    build=build,
                    progression=progression.progression,
                    active_bar=active_bar,
                )
                context_unresolved, context_boundaries = self._partition_context_messages_with_cp(
                    context.unresolved_gear_effects
                )
                unresolved.extend(context_unresolved)
                boundaries.extend(context_boundaries)
            except Exception as exc:
                unresolved.append(f"{active_bar} static build resolution failed: {exc}")

            skill_gaps: list[str] = []
            bar_skill_effects = self._skill_variants(build, active_bar, skill_gaps)
            unresolved.extend(skill_gaps)
            capability_unresolved.extend(skill_gaps)
            if bar_skill_effects:
                sources.append(f"{active_bar}:skills")
                effects.extend(bar_skill_effects)

            gear_gaps: list[str] = []
            bar_gear_effects = self._gear_variants(build, active_bar, gear_gaps)
            unresolved.extend(gear_gaps)
            capability_unresolved.extend(gear_gaps)
            if bar_gear_effects:
                sources.append(f"{active_bar}:gear")
                effects.extend(bar_gear_effects)

        potion_name = self._clean(build.Potion)
        if potion_name:
            potion = self.potions.resolve(potion_name)
            unresolved.extend(potion.unresolved)
            capability_unresolved.extend(potion.unresolved)
            if potion.effects:
                sources.append("potion:availability")
                effects.extend(potion.effects)
                boundaries.append(
                    f"Potion availability resolved without standing uptime: {potion_name}"
                )
                if getattr(potion, "capability_resolved", False) and not getattr(potion, "resolved", False):
                    boundaries.append(
                        "Potion effect family resolved from exact saved-label semantics and "
                        f"canonical database effects; recipe/formula provenance unavailable: {potion_name}"
                    )

        deduped: list[EffectVariant] = []
        seen: set[tuple[str, str, str, str]] = set()
        for effect in effects:
            key = (
                effect.name,
                str(effect.layer),
                str(effect.source),
                str(effect.condition or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(effect)

        conditional = tuple(
            sorted({effect.source for effect in deduped if effect.condition or effect.trigger})
        )
        return SavedBuildCapabilityAudit(
            character_name=build.Name,
            build_name=build.BuildName,
            character_id=progression.character_id,
            resolved_sources=tuple(sorted(set(sources))),
            resolved_effects=tuple(deduped),
            conditional_sources=conditional,
            unresolved=tuple(dict.fromkeys(unresolved)),
            capability_unresolved=tuple(dict.fromkeys(capability_unresolved)),
            boundaries=tuple(dict.fromkeys(boundaries)),
        )
