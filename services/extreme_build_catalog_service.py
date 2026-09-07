from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
from typing import Any

from minmax.character_build.character_class import CLASS_SKILL_LINES, CharacterClass
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.passive_math import (
    WARDEN_ADVANCED_SPECIES_CRIT_DAMAGE_PER_SLOTTED,
    WARDEN_FLOURISH_RECOVERY_PERCENT,
    WARDEN_FROZEN_ARMOR_RESISTANCE_PER_SLOTTED,
)
from services.extreme_class_configuration_service import ExtremeClassConfigurationService
from services.extreme_skill_standing_effect_service import (
    ExtremeSkillEffectScope,
    ExtremeSkillStandingEffectService,
)
from services.extreme_subclass_skill_bar_service import ExtremeSubclassSkillBarService
from services.skill_bar_eligibility import is_player_active, is_ultimate
from services.skill_choice_service import load_skill_choices


CATALOG_SCHEMA_VERSION = 1
SUBCLASS_RULE_VERSION = "phase13.2-three-lines-max-two-foreign-distinct-classes"

# These are the reviewed objective families whose slot-count passives can be
# represented as reusable formulas. We intentionally cache formulas, not final
# scores, because some values still depend on the caller's current reference stat.
_REVIEWED_PASSIVE_OBJECTIVES = (
    "critical_damage",
    "magicka_recovery",
    "physical_resistance",
    "spell_critical",
    "spell_damage",
    "spell_resistance",
    "stamina_recovery",
    "weapon_critical",
    "weapon_damage",
)

_LINE_OWNER: dict[str, CharacterClass] = {
    line: character_class
    for character_class, lines in CLASS_SKILL_LINES.items()
    for line in lines
}


@dataclass(frozen=True)
class ExtremePassiveFormula:
    objective_key: str
    flat: float = 0.0
    ratio: float = 0.0
    percent_of_reference: float = 0.0
    sources: tuple[str, ...] = ()


class ExtremeBuildCatalogService:
    """Build and persist the reusable structural universe for Extreme Build Lab.

    The catalog deliberately precomputes only facts that remain valid across
    optimization requests. Objective context such as active bar, potion state,
    group providers, current reference values, sets, and encounter/runtime state
    stays dynamic and is never fossilized into the catalog.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def build(self) -> dict[str, Any]:
        configurations = ExtremeClassConfigurationService.all_candidates()

        # WHY PRECOMPUTE THIS: subclass legality is structural and changes only
        # when ESO subclass rules change. Re-enumerating it for every requested
        # stat provides no new information, so we cache the legal universe once.
        configuration_rows = [
            {
                "base_class": row.base_class.value,
                "equipped_skill_lines": list(row.equipped_skill_lines),
                "is_pure_class": row.is_pure_class,
                "class_mastery_available": row.class_mastery_available,
                "foreign_skill_lines": list(row.foreign_skill_lines),
            }
            for row in configurations
        ]

        unique_line_sets = sorted(
            {tuple(row.equipped_skill_lines) for row in configurations}
        )

        # WHY PRECOMPUTE THIS: each three-line configuration has only 28 possible
        # six-slot count distributions. The count shapes are objective-neutral,
        # so runtime optimization should not regenerate them thousands of times.
        allocation_rows = {
            self._line_set_key(lines): [
                {"slot_counts": [[line, count] for line, count in allocation]}
                for allocation in self._six_slot_allocations(lines)
            ]
            for lines in unique_line_sets
        }

        # WHY PRECOMPUTE THIS: the canonical skill-family membership, morphs,
        # line ownership, and Ultimate classification come from eso.db and are
        # expensive catalog work. We store alternatives, not a winning morph,
        # because external buffs can change which morph has marginal value.
        skill_families = self._skill_family_catalog()

        # WHY PRECOMPUTE THIS: slot-count passive math is deterministic once the
        # line distribution is known. We cache coefficient/formula descriptors
        # instead of a final number so reference-dependent effects such as
        # Flourish remain correct for whichever character is scored later.
        passive_formulas = {
            self._line_set_key(lines): [
                {
                    "slot_counts": [[line, count] for line, count in allocation],
                    "formulas": [
                        asdict(formula)
                        for objective in _REVIEWED_PASSIVE_OBJECTIVES
                        if (
                            formula := self._passive_formula(
                                lines,
                                dict(allocation),
                                objective,
                            )
                        )
                        is not None
                    ],
                }
                for allocation in self._six_slot_allocations(lines)
            ]
            for lines in unique_line_sets
        }

        return {
            "metadata": {
                "schema_version": CATALOG_SCHEMA_VERSION,
                "subclass_rule_version": SUBCLASS_RULE_VERSION,
                "source_database_sha256": self.database_fingerprint(),
                "source_database_name": self.database_path.name,
                "active_bar_slots": 6,
                "_why": (
                    "The fingerprint invalidates this cache when canonical ESO data changes; "
                    "the rule version invalidates it when subclass legality changes."
                ),
            },
            "class_configurations": {
                "_why": (
                    "Legal class-line ownership is structural. Runtime requests should filter "
                    "and score this list instead of rebuilding subclass legality."
                ),
                "rows": configuration_rows,
            },
            "bar_allocations": {
                "_why": (
                    "Six-slot line-count shapes are objective-neutral and finite. Precomputing "
                    "them removes repeated combinatoric enumeration from route scoring."
                ),
                "by_line_set": allocation_rows,
            },
            "skill_families": {
                "_why": (
                    "Ability families, morph alternatives, line ownership, and Ultimate status "
                    "come from canonical data. We retain alternatives so dynamic buff context "
                    "can still choose the best marginal morph later."
                ),
                "by_skill_line": skill_families,
            },
            "passive_allocation_formulas": {
                "_why": (
                    "Reviewed slot-count passive effects are deterministic formulas. We cache "
                    "flat/ratio/reference coefficients, not final context-dependent scores."
                ),
                "by_line_set": passive_formulas,
            },
            "dynamic_runtime_inputs": {
                "_why": (
                    "These values intentionally remain outside the cache because they can change "
                    "the winner without changing structural legality."
                ),
                "items": [
                    "requested objective",
                    "selected active bar",
                    "reference stat values",
                    "potion state",
                    "set effects",
                    "external/group named buffs",
                    "runtime activation and uptime",
                    "encounter state",
                ],
            },
        }

    def write(self, output_path: str | Path) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(self.build(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output

    def database_fingerprint(self) -> str:
        digest = sha256()
        with self.database_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _line_set_key(lines: tuple[str, ...]) -> str:
        return "|".join(sorted(lines))

    @staticmethod
    def _six_slot_allocations(
        lines: tuple[str, ...],
    ) -> tuple[tuple[tuple[str, int], ...], ...]:
        canonical = tuple(sorted(lines))
        rows: list[tuple[tuple[str, int], ...]] = []
        for counts in product(range(7), repeat=len(canonical)):
            if sum(counts) != 6:
                continue
            rows.append(tuple(zip(canonical, counts)))
        return tuple(rows)

    def _skill_family_catalog(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, dict[tuple[int, bool], list[dict[str, Any]]]] = {}
        for row in load_skill_choices(self.database_path):
            if not is_player_active(row):
                continue
            line_id = ExtremeSubclassSkillBarService.canonical_line_id(row.get("skill_line"))
            if line_id is None:
                continue
            ability_id = int(row.get("ability_id") or 0)
            base_id = int(row.get("base_ability_id") or ability_id or 0)
            if ability_id <= 0 or base_id <= 0:
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            ultimate = bool(is_ultimate(row))
            effects = self._standing_effect_descriptors(name)
            grouped.setdefault(line_id, {}).setdefault((base_id, ultimate), []).append(
                {
                    "ability_id": ability_id,
                    "base_ability_id": base_id,
                    "name": name,
                    "morph": int(row.get("morph") or 0),
                    "is_ultimate": ultimate,
                    "standing_effects": effects,
                }
            )

        result: dict[str, list[dict[str, Any]]] = {}
        for line_id, families in sorted(grouped.items()):
            result[line_id] = [
                {
                    "base_ability_id": base_id,
                    "is_ultimate": ultimate,
                    "alternatives": sorted(
                        alternatives,
                        key=lambda item: (
                            item["name"].casefold(),
                            item["morph"],
                            item["ability_id"],
                        ),
                    ),
                }
                for (base_id, ultimate), alternatives in sorted(families.items())
            ]
        return result

    @staticmethod
    def _standing_effect_descriptors(skill_name: str) -> list[dict[str, Any]]:
        # reference_value=1 lets us expose reference-sensitive reviewed effects
        # as descriptors without pretending that 1 is the caller's real stat.
        effects = ExtremeSkillStandingEffectService.effects_for_skill(
            skill_name,
            reference_value=1.0,
        )
        descriptors: list[dict[str, Any]] = []
        for effect in effects:
            reference_sensitive = effect.stacking_key in {
                "major_brutality",
                "major_sorcery",
            }
            descriptors.append(
                {
                    "objective_key": effect.objective_key,
                    "scope": effect.scope.value,
                    "stacking_key": effect.stacking_key,
                    "source": effect.source,
                    "reference_sensitive": reference_sensitive,
                    "coefficient": (
                        ExtremeSkillStandingEffectService.MAJOR_BRUTALITY_SORCERY_PERCENT
                        if reference_sensitive
                        else None
                    ),
                    "flat_or_ratio_delta": None if reference_sensitive else effect.projected_delta,
                }
            )
        return descriptors

    @staticmethod
    def _passive_formula(
        lines: tuple[str, ...],
        allocation: dict[str, int],
        objective_key: str,
    ) -> ExtremePassiveFormula | None:
        flat = 0.0
        ratio = 0.0
        percent = 0.0
        sources: list[str] = []

        if "assassination" in lines and objective_key in {"weapon_critical", "spell_critical"}:
            nightblade_slots = sum(
                allocation.get(line, 0)
                for line in lines
                if _LINE_OWNER.get(line) is CharacterClass.NIGHTBLADE
            )
            if nightblade_slots:
                rating = (
                    ExtremeSubclassSkillBarService.__name__  # keep source module import intentional
                    and 438.0 * nightblade_slots
                )
                ratio += GearStatInputResolver.critical_rating_to_ratio(rating)
                sources.append(f"Pressure Points ({nightblade_slots} Nightblade slots)")

        if "storm_calling" in lines and objective_key in {"weapon_damage", "spell_damage"}:
            sorcerer_slots = sum(
                allocation.get(line, 0)
                for line in lines
                if _LINE_OWNER.get(line) is CharacterClass.SORCERER
            )
            if sorcerer_slots:
                flat += 108.0 * sorcerer_slots
                sources.append(f"Expert Mage ({sorcerer_slots} Sorcerer slots)")

        animal_slots = allocation.get("animal_companions", 0)
        if "animal_companions" in lines and animal_slots:
            if objective_key == "critical_damage":
                ratio += WARDEN_ADVANCED_SPECIES_CRIT_DAMAGE_PER_SLOTTED * animal_slots
                sources.append(f"Advanced Species ({animal_slots} Animal Companions slots)")
            elif objective_key in {"magicka_recovery", "stamina_recovery"}:
                percent += WARDEN_FLOURISH_RECOVERY_PERCENT
                sources.append("Flourish (Animal Companions represented)")

        winter_slots = allocation.get("winters_embrace", 0)
        if (
            "winters_embrace" in lines
            and winter_slots
            and objective_key in {"physical_resistance", "spell_resistance"}
        ):
            flat += WARDEN_FROZEN_ARMOR_RESISTANCE_PER_SLOTTED * winter_slots
            sources.append(f"Frozen Armor ({winter_slots} Winter's Embrace slots)")

        if not sources:
            return None
        return ExtremePassiveFormula(
            objective_key=objective_key,
            flat=flat,
            ratio=ratio,
            percent_of_reference=percent,
            sources=tuple(sources),
        )
