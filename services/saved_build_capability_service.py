from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.effect_instance import EffectVariant
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.skill_effect_repository import SkillEffectRepository
from models.build_model import GearSlot, PlayerBuild
from services.build_service import BuildService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter


@dataclass(frozen=True)
class SavedBuildCapabilityAudit:
    character_name: str
    build_name: str
    character_id: str
    resolved_effects: tuple[EffectVariant, ...] = ()
    resolved_sources: tuple[str, ...] = ()
    conditional_sources: tuple[str, ...] = ()
    boundaries: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.character_id) and not self.unresolved


class SavedBuildCapabilityService:
    """Audit one real saved build through Phase 5 production resolvers.

    This service reports evidence rather than inventing uptime. Intentional
    static/temporal boundaries are separated from genuine unresolved evidence.
    """

    TWO_PIECE_WEAPON_MARKERS = (
        "staff",
        "bow",
        "two-handed",
        "greatsword",
        "battle axe",
        "maul",
    )
    INTENTIONAL_BOUNDARY_PREFIXES = (
        "Potion selected; activation/uptime is not part of static build state:",
    )
    CP_DYNAMIC_PREFIX = "Champion Point is dynamic or not yet stat-mapped:"

    # These purchased CP stars are verified by canonical tooltip text but do
    # not belong in the Phase 5 standing/core-stat layer. Keep them explicit as
    # capability boundaries instead of pretending their conditional/runtime
    # semantics are unresolved defects in saved-build persistence.
    CP_DEFERRED_BOUNDARY_REASONS = {
        "battle mastery": "status-effect chance model",
        "flawless ritual": "status-effect chance model",
        "elemental aegis": "typed incoming-damage mitigation model",
        "hardy": "typed incoming-damage mitigation model",
        "preparation": "attacker-type incoming-damage mitigation model",
        "mighty": "attack-damage-type conditional offensive model",
        "war mage": "attack-damage-type conditional offensive model",
        "bashing brutality": "bash-damage combat utility channel",
        "defiance": "Break Free cost combat utility channel",
        "savage defense": "Bash cost combat utility channel",
        "sprinter": "Sprint cost combat utility channel",
        "tumbling": "Roll Dodge cost combat utility channel",
        "hasty": "conditional movement-speed model",
        "nimble protector": "conditional movement-speed model",
        "celerity": "movement-speed model",
        "mystic tenacity": "incoming status-effect duration model",
        "tempered soul": "resurrection-state model",
        "piercing gaze": "stealth-detection/PvP utility model",
    }

    def __init__(self, build_service: BuildService, database_path: str | Path) -> None:
        self.build_service = build_service
        self.database_path = Path(database_path)
        self.progression = MinmaxCharacterProgressionAdapter(
            build_service.canonical.catalog_service
        )
        self.gear_repository = GearSetRepository(self.database_path)
        self.gear_effects = GearSetEffectVariantResolver(self.gear_repository)
        self.skill_effects = SkillEffectRepository(self.database_path)
        self.potions = PotionAvailabilityRepository(self.database_path)
        self.context_factory = BuildCalculationContextFactory(
            gear_set_repository=self.gear_repository
        )

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _weapon_piece_count(cls, slot: GearSlot) -> int:
        weapon_type = cls._clean(slot.WeaponType).casefold()
        return 2 if any(marker in weapon_type for marker in cls.TWO_PIECE_WEAPON_MARKERS) else 1

    @classmethod
    def _active_set_counts(cls, build: PlayerBuild, active_bar: str) -> Counter[str]:
        counts: Counter[str] = Counter()
        for entry in build.Armor.values():
            name = cls._clean(entry.get("Set"))
            if name:
                counts[name] += 1
        for slot in (build.Necklace, build.Ring1, build.Ring2):
            name = cls._clean(slot.Set)
            if name:
                counts[name] += 1
        main, offhand = build.active_weapon_slots(active_bar)
        for slot in (main, offhand):
            name = cls._clean(slot.Set)
            if name:
                counts[name] += cls._weapon_piece_count(slot)
        return counts

    def _ability_id(self, name: str, class_name: str) -> int | None:
        if not self.database_path.exists():
            return None
        with sqlite3.connect(self.database_path) as db:
            columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)")}
            if not {"ability_id", "name"}.issubset(columns):
                return None
            clauses = ["lower(trim(name)) = lower(trim(?))"]
            params: list[object] = [name]
            if class_name and "class_type" in columns:
                clauses.append("(trim(coalesce(class_type,'')) = '' OR lower(trim(class_type)) = lower(trim(?)))")
                params.append(class_name)
            order = "rank DESC, morph DESC, ability_id DESC" if {"rank", "morph"}.issubset(columns) else "ability_id DESC"
            row = db.execute(
                f"SELECT ability_id FROM ability WHERE {' AND '.join(clauses)} ORDER BY {order} LIMIT 1",
                params,
            ).fetchone()
        return int(row[0]) if row else None

    def _skill_variants(self, build: PlayerBuild, active_bar: str, unresolved: list[str]) -> list[EffectVariant]:
        skills = build.BackBarSkills if active_bar == "back" else build.FrontBarSkills
        variants: list[EffectVariant] = []
        for raw_name in skills:
            name = self._clean(raw_name)
            if not name:
                continue
            ability_id = self._ability_id(name, build.EsoClass)
            if ability_id is None:
                unresolved.append(f"{active_bar} skill not found in canonical ability data: {name}")
                continue
            variants.extend(self.skill_effects.resolve(ability_id))
        return variants

    def _gear_variants(self, build: PlayerBuild, active_bar: str, unresolved: list[str]) -> list[EffectVariant]:
        variants: list[EffectVariant] = []
        for set_name, count in self._active_set_counts(build, active_bar).items():
            gear_set = self.gear_repository.get_set(set_name)
            if gear_set is None:
                unresolved.append(f"{active_bar} gear set not found in canonical data: {set_name}")
                continue
            variants.extend(self.gear_effects.resolve(gear_set.id, count))
        return variants

    def _cp_discipline(self, cp_name: str) -> int | None:
        if not self.database_path.exists():
            return None
        try:
            with sqlite3.connect(self.database_path) as db:
                row = db.execute(
                    "SELECT discipline_id FROM champion_point WHERE lower(trim(name)) = lower(trim(?)) LIMIT 1",
                    (cp_name,),
                ).fetchone()
            return int(row[0]) if row and row[0] is not None else None
        except sqlite3.Error:
            return None

    @classmethod
    def _partition_context_messages(cls, messages: tuple[str, ...]) -> tuple[list[str], list[str]]:
        """Partition context messages without requiring repository access.

        This remains callable at class level for compatibility with existing
        callers/tests. Database-aware CP discipline classification is layered
        on separately by ``_partition_context_messages_with_cp``.
        """
        unresolved: list[str] = []
        boundaries: list[str] = []
        for message in messages:
            if any(message.startswith(prefix) for prefix in cls.INTENTIONAL_BOUNDARY_PREFIXES):
                boundaries.append(message)
                continue
            if message.endswith("requires status-effect chance model"):
                boundaries.append(message)
                continue
            unresolved.append(message)
        return unresolved, boundaries

    def _partition_context_messages_with_cp(
        self,
        messages: tuple[str, ...],
    ) -> tuple[list[str], list[str]]:
        unresolved, boundaries = self._partition_context_messages(messages)
        remaining: list[str] = []
        for message in unresolved:
            if message.startswith(self.CP_DYNAMIC_PREFIX):
                cp_name = self._clean(message[len(self.CP_DYNAMIC_PREFIX):])
                if self._cp_discipline(cp_name) == 3:
                    boundaries.append(
                        f"Non-combat Champion Point outside combat capability audit: {cp_name}"
                    )
                    continue
                reason = self.CP_DEFERRED_BOUNDARY_REASONS.get(cp_name.casefold())
                if reason:
                    boundaries.append(
                        f"Deferred Champion Point capability ({reason}): {cp_name}"
                    )
                    continue
            remaining.append(message)
        return remaining, boundaries

    def audit_build(self, build: PlayerBuild) -> SavedBuildCapabilityAudit:
        unresolved: list[str] = []
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

            bar_skill_effects = self._skill_variants(build, active_bar, unresolved)
            if bar_skill_effects:
                sources.append(f"{active_bar}:skills")
                effects.extend(bar_skill_effects)

            bar_gear_effects = self._gear_variants(build, active_bar, unresolved)
            if bar_gear_effects:
                sources.append(f"{active_bar}:gear")
                effects.extend(bar_gear_effects)

        potion_name = self._clean(build.Potion)
        if potion_name:
            potion = self.potions.resolve(potion_name)
            unresolved.extend(potion.unresolved)
            if potion.effects:
                sources.append("potion:availability")
                effects.extend(potion.effects)
                boundaries.append(
                    f"Potion availability resolved without standing uptime: {potion_name}"
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
            resolved_effects=tuple(deduped),
            resolved_sources=tuple(dict.fromkeys(sources)),
            conditional_sources=conditional,
            boundaries=tuple(dict.fromkeys(message for message in boundaries if message)),
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
        )

    def audit_roster(self) -> tuple[SavedBuildCapabilityAudit, ...]:
        roster = self.build_service.load()
        return tuple(
            self.audit_build(build)
            for build in roster.Members
            if self._clean(build.Name) or self._clean(build.Gamertag) or self._clean(build.BuildName)
        )
