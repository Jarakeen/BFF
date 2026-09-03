from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from minmax.character_build.effect_instance import EffectVariant
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from minmax.potion_availability_repository import PotionAvailabilityRepository
from minmax.skill_effect_repository import SkillEffectRepository
from models.build_model import PlayerBuild
from models.scribing_recipe import ScribedSkillRecipe
from services.build_service import BuildService
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.scribing_catalog import is_grimoire_compatible


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

    @property
    def capability_resolution_gaps(self) -> tuple[str, ...]:
        """Backward-compatible alias for Phase 10 capability-only gaps."""
        return self.capability_unresolved


class SavedBuildCapabilityService:
    """Resolve what a saved build can provide without pretending runtime uptime exists."""

    _INTENTIONAL_STATIC_BOUNDARY_PREFIXES = (
        "Potion selected; activation/uptime is not part of static build state:",
        "Conditional racial passive bonus requires combat-state model:",
        "Racial ability-cost reduction requires cost-stat model:",
        "Non-combat racial passive outside combat capability audit:",
    )
    _CP_DYNAMIC_PREFIX = "Champion Point is dynamic or not yet stat-mapped:"
    _CP_DEFERRED_BOUNDARY_REASONS = {
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
        self.database_path = Path(database_path)
        self.context_factory = context_factory or Phase5BuildCalculationContextFactory(self.database_path)
        self.progression = progression or MinmaxCharacterProgressionAdapter(
            builds.canonical.catalog_service
        )
        self.skills = skills or SkillEffectRepository(self.database_path)
        self.gear_repository = None if gear is not None else GearSetRepository(self.database_path)
        self.gear = gear or GearSetEffectVariantResolver(self.gear_repository)
        self.potions = potions or PotionAvailabilityRepository(self.database_path)
        self._ability_id_cache: dict[tuple[str, str], int | None] = {}
        self._ability_is_crafted_cache: dict[int, bool] = {}
        # Instance-scoped on purpose: a new service/process sees a fresh database snapshot.
        self._audit_cache: dict[str, SavedBuildCapabilityAudit] = {}

    @staticmethod
    def _clean(value) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _build_cache_key(build: PlayerBuild) -> str:
        payload = json.dumps(
            build.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

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
            elif text.endswith("requires status-effect chance model"):
                boundaries.append(text)
            else:
                unresolved.append(text)
        return unresolved, boundaries

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

    def _partition_context_messages_with_cp(self, messages) -> tuple[list[str], list[str]]:
        unresolved, boundaries = self._partition_context_messages(messages)
        kept: list[str] = []
        for text in unresolved:
            if text.startswith(self._CP_DYNAMIC_PREFIX):
                cp_name = self._clean(text[len(self._CP_DYNAMIC_PREFIX):])
                if self._cp_discipline(cp_name) == 3:
                    boundaries.append(
                        f"Non-combat Champion Point outside combat capability audit: {cp_name}"
                    )
                    continue
                reason = self._CP_DEFERRED_BOUNDARY_REASONS.get(cp_name.casefold())
                if reason:
                    boundaries.append(
                        f"Deferred Champion Point capability ({reason}): {cp_name}"
                    )
                    continue
            if text.startswith("Champion Point star ") and "does not resolve to a canonical effect" in text:
                boundaries.append(text)
            else:
                kept.append(text)
        return kept, boundaries

    def _ability_id(self, name: str, class_name: str) -> int | None:
        cache_key = (
            str(name or "").strip().casefold(),
            str(class_name or "").strip().casefold(),
        )
        if cache_key in self._ability_id_cache:
            return self._ability_id_cache[cache_key]
        if not self.database_path.exists():
            return None
        try:
            with sqlite3.connect(self.database_path) as db:
                columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)")}
                if not {"ability_id", "name"}.issubset(columns):
                    self._ability_id_cache[cache_key] = None
                    return None
                clauses = ["lower(trim(name)) = lower(trim(?))"]
                params: list[object] = [name]
                if class_name and "class_type" in columns:
                    clauses.append(
                        "(trim(coalesce(class_type,'')) = '' OR lower(trim(class_type)) = lower(trim(?)))"
                    )
                    params.append(class_name)
                order = (
                    "rank DESC, morph DESC, ability_id DESC"
                    if {"rank", "morph"}.issubset(columns)
                    else "ability_id DESC"
                )
                row = db.execute(
                    f"SELECT ability_id FROM ability WHERE {' AND '.join(clauses)} ORDER BY {order} LIMIT 1",
                    params,
                ).fetchone()
        except sqlite3.Error:
            return None
        result = int(row[0]) if row else None
        self._ability_id_cache[cache_key] = result
        return result

    def _ability_is_crafted(self, ability_id: int) -> bool:
        cache_key = int(ability_id)
        if cache_key in self._ability_is_crafted_cache:
            return self._ability_is_crafted_cache[cache_key]
        if not self.database_path.exists():
            self._ability_is_crafted_cache[cache_key] = False
            return False
        try:
            with sqlite3.connect(self.database_path) as db:
                columns = {str(row[1]) for row in db.execute("PRAGMA table_info(ability)")}
                if "is_crafted" not in columns:
                    self._ability_is_crafted_cache[cache_key] = False
                    return False
                row = db.execute(
                    "SELECT is_crafted FROM ability WHERE ability_id = ? LIMIT 1",
                    (ability_id,),
                ).fetchone()
            result = bool(row and int(row[0] or 0) == 1)
        except (sqlite3.Error, TypeError, ValueError):
            result = False
        self._ability_is_crafted_cache[cache_key] = result
        return result

    @classmethod
    def _configured_scribing_recipe(
        cls, build: PlayerBuild, result_name: str
    ) -> ScribedSkillRecipe | None:
        target = cls._clean(result_name).casefold()
        for raw in getattr(build, "ScribedSkillRecipes", []) or []:
            recipe = raw if isinstance(raw, ScribedSkillRecipe) else ScribedSkillRecipe.from_dict(raw)
            if cls._clean(recipe.ResultName).casefold() == target:
                return recipe
        return None

    @staticmethod
    def _recipe_is_canonically_consistent(recipe: ScribedSkillRecipe) -> bool:
        if not recipe.is_complete:
            return False
        return all(
            is_grimoire_compatible(kind, script, recipe.Grimoire)
            for kind, script in (
                ("focus", recipe.Focus),
                ("signature", recipe.Signature),
                ("affix", recipe.Affix),
            )
        )

    def _canonical_gear_entity_exists(self, set_name: str) -> bool:
        if not self.database_path.exists():
            return False
        try:
            with sqlite3.connect(self.database_path) as db:
                tables = {
                    str(row[0])
                    for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                }
                if "entity" not in tables:
                    return False
                row = db.execute(
                    "SELECT id FROM entity WHERE entity_type='gear_set' "
                    "AND lower(trim(name))=lower(trim(?)) LIMIT 1",
                    (set_name,),
                ).fetchone()
                if row is None:
                    return False
                if "entity_source" not in tables:
                    return True
                source = db.execute(
                    "SELECT 1 FROM entity_source WHERE entity_id=? LIMIT 1",
                    (row[0],),
                ).fetchone()
                return source is not None
        except sqlite3.Error:
            return False

    def _skill_variants(
        self,
        build: PlayerBuild,
        active_bar: str,
        unresolved: list[str],
        boundaries: list[str],
    ) -> list[EffectVariant]:
        names = build.FrontBarSkills if active_bar == "front" else build.BackBarSkills
        variants: list[EffectVariant] = []
        for name in names:
            name = self._clean(name)
            if not name:
                continue
            ability_id = self._ability_id(name, build.EsoClass)
            if ability_id is None:
                unresolved.append(f"{active_bar} skill not found in canonical ability data: {name}")
                continue
            if self._ability_is_crafted(ability_id):
                recipe = self._configured_scribing_recipe(build, name)
                if recipe is None or not recipe.is_complete:
                    unresolved.append(
                        f"{active_bar} scribed skill requires configured recipe semantics before capability resolution: {name}"
                    )
                    continue
                if not self._recipe_is_canonically_consistent(recipe):
                    unresolved.append(
                        f"{active_bar} scribed skill recipe conflicts with canonical script compatibility: {name}"
                    )
                    continue
                boundaries.append(
                    f"{active_bar} configured scribed skill recipe resolved; detailed scripted effect conversion deferred: "
                    f"{name} [{recipe.Grimoire} | {recipe.Focus} | {recipe.Signature} | {recipe.Affix}]"
                )
                continue
            resolved = self.skills.resolve(ability_id)
            if hasattr(resolved, "unresolved") and hasattr(resolved, "effects"):
                unresolved.extend(resolved.unresolved)
                variants.extend(resolved.effects)
            else:
                variants.extend(resolved)
        return variants

    def _gear_variants(
        self,
        build: PlayerBuild,
        active_bar: str,
        unresolved: list[str],
        boundaries: list[str],
    ) -> list[EffectVariant]:
        variants: list[EffectVariant] = []
        for set_name, pieces in self._active_set_counts(build, active_bar).items():
            if self.gear_repository is None:
                resolved = self.gear.resolve(set_name, active_pieces=pieces)
                if hasattr(resolved, "unresolved") and hasattr(resolved, "effects"):
                    unresolved.extend(resolved.unresolved)
                    variants.extend(resolved.effects)
                else:
                    variants.extend(resolved)
                continue
            gear_set = self.gear_repository.get_set(set_name)
            if gear_set is None:
                if self._canonical_gear_entity_exists(set_name):
                    boundaries.append(
                        f"{active_bar} gear set identity resolved from canonical entity/source data; "
                        f"legacy gear_set effect semantics unavailable: {set_name}"
                    )
                    continue
                unresolved.append(f"{active_bar} gear set not found in canonical data: {set_name}")
                continue
            variants.extend(self.gear.resolve(gear_set.id, pieces))
        return variants

    def audit_build(self, build: PlayerBuild) -> SavedBuildCapabilityAudit:
        cache_key = self._build_cache_key(build)
        cached = self._audit_cache.get(cache_key)
        if cached is not None:
            return cached

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
            bar_skill_effects = self._skill_variants(build, active_bar, skill_gaps, boundaries)
            unresolved.extend(skill_gaps)
            capability_unresolved.extend(skill_gaps)
            if bar_skill_effects:
                sources.append(f"{active_bar}:skills")
                effects.extend(bar_skill_effects)

            gear_gaps: list[str] = []
            bar_gear_effects = self._gear_variants(build, active_bar, gear_gaps, boundaries)
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
        result = SavedBuildCapabilityAudit(
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
        self._audit_cache[cache_key] = result
        return result

    def audit_roster(self) -> tuple[SavedBuildCapabilityAudit, ...]:
        roster = self.builds.load()
        return tuple(
            self.audit_build(build)
            for build in roster.Members
            if self._clean(build.Name) or self._clean(build.Gamertag) or self._clean(build.BuildName)
        )