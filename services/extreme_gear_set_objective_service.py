from __future__ import annotations

"""Project canonical gear-set bonuses into Extreme objective units.

This adapter is intentionally stricter than the tolerant saved-build gear layer.
Every active canonical bonus row is inspected. If the shared gear-set resolver
cannot interpret an active bonus, the bonus normally remains an explicit blocker
rather than silently contributing zero.

For Max Health/Magicka/Stamina only, an additional conservative screening layer
may prove an *unmapped* bonus irrelevant when its description cannot modify the
requested maximum resource and does not alter the legal equipment search. That
narrow exception avoids requiring the entire unrelated proc corpus to be mechanic-
mapped before a max-resource denominator can close while preserving fail-closed
behavior for resource references and global equipment-state mechanics.
"""

from dataclasses import dataclass

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.eso_markup import normalize_eso_markup
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.gear_sets import GearSet, GearSetBonus
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.stat_ids import StatId
from services.extreme_gear_set_resource_objective_screening_service import (
    ExtremeGearSetResourceObjectiveScreeningService,
)


@dataclass(frozen=True)
class ExtremeGearSetObjectiveCandidate:
    set_id: int
    set_name: str
    category: str | None
    equipped_piece_count: int
    objective_key: str
    reviewed_delta: float
    source_bonuses: tuple[GearSetBonus, ...] = ()
    source_effects: tuple[Effect, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved


class ExtremeGearSetObjectiveService:
    """Enumerate reviewed lower-bound set contributions without hiding gaps."""

    REVIEWED_OBJECTIVES = (
        "critical_damage",
        "critical_healing",
        "healing_done",
        "max_health",
        "max_magicka",
        "max_stamina",
        "magicka_recovery",
        "stamina_recovery",
        "physical_resistance",
        "spell_resistance",
        "spell_damage",
        "weapon_damage",
        "spell_critical",
        "weapon_critical",
        "detection_radius_reduction",
        "sneak_cost_reduction",
    )
    _MAX_RESOURCE_OBJECTIVES = frozenset({"max_health", "max_magicka", "max_stamina"})
    # These conditions are explicit legal states.  For objective *relevance* we
    # only need to know that a positive resource bonus can exist under the state;
    # the later structural/runtime scorer still owns proving the state is active
    # for any winning candidate.
    _MAX_RESOURCE_RELEVANCE_CONDITIONS = frozenset(
        {
            "armor_ability_slotted",
            "destruction_staff_equipped",
            "drink_buff_active",
            "food_buff_active",
            "pet_active",
            "transformed",
        }
    )

    _STAT_BY_OBJECTIVE = {
        "critical_damage": StatId.CRITICAL_DAMAGE,
        "critical_healing": StatId.CRITICAL_HEALING,
        "healing_done": StatId.HEALING_DONE,
        "max_health": StatId.MAX_HEALTH,
        "max_magicka": StatId.MAX_MAGICKA,
        "max_stamina": StatId.MAX_STAMINA,
        "magicka_recovery": StatId.MAGICKA_RECOVERY,
        "stamina_recovery": StatId.STAMINA_RECOVERY,
        "physical_resistance": StatId.PHYSICAL_RESISTANCE,
        "spell_resistance": StatId.SPELL_RESISTANCE,
        "spell_damage": StatId.SPELL_DAMAGE,
        "weapon_damage": StatId.WEAPON_DAMAGE,
        "detection_radius_reduction": StatId.DETECTION_RADIUS_REDUCTION,
        "sneak_cost_reduction": StatId.SNEAK_COST_REDUCTION,
    }

    @classmethod
    def _target_stats(cls, objective_key: str) -> set[StatId]:
        objective = str(objective_key).strip().casefold()
        if objective not in cls.REVIEWED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme gear-set objective: {objective_key!r}")
        if objective in {"spell_critical", "weapon_critical"}:
            return {StatId.CRITICAL_CHANCE, StatId.SPELL_CRITICAL, StatId.WEAPON_CRITICAL}
        stat = cls._STAT_BY_OBJECTIVE.get(objective)
        return set() if stat is None else {stat}

    @staticmethod
    def _active_bonuses(repository: GearSetRepository, set_id: int, piece_count: int) -> tuple[GearSetBonus, ...]:
        return tuple(
            bonus
            for bonus in repository.get_bonuses(set_id)
            if bonus.piece_count <= piece_count
        )

    @staticmethod
    def _maximum_useful_piece_count(repository: GearSetRepository, gear_set: GearSet) -> int:
        bonuses = repository.get_bonuses(gear_set.id)
        highest_bonus = max((bonus.piece_count for bonus in bonuses), default=0)
        configured = int(gear_set.max_equip_count or 0)
        if configured > 0 and highest_bonus > 0:
            return min(configured, highest_bonus)
        return configured or highest_bonus

    @classmethod
    def _project_relevant_effect(
        cls,
        effect: Effect,
        objective_key: str,
    ) -> tuple[float | None, str | None]:
        objective = str(objective_key).strip().casefold()

        if effect.condition:
            condition = str(effect.condition).strip()
            if not (
                objective in cls._MAX_RESOURCE_OBJECTIVES
                and condition in cls._MAX_RESOURCE_RELEVANCE_CONDITIONS
            ):
                return None, f"{effect.source}: relevant set effect requires condition {effect.condition}"

        if effect.operation is EffectOperation.ADD:
            value = float(effect.value)
            if objective in {"spell_critical", "weapon_critical"}:
                return GearStatInputResolver.critical_rating_to_ratio(value), None
            return value, None

        if effect.operation is EffectOperation.ADD_PERCENT:
            if objective in {
                "critical_damage",
                "critical_healing",
                "healing_done",
                "sneak_cost_reduction",
            }:
                value = float(effect.value)
                if effect.unit is EffectUnit.PERCENT:
                    value /= 100.0
                return value, None
            return None, (
                f"{effect.source}: relevant percentage set effect requires "
                f"objective-specific stacking/reference review"
            )

        return None, f"{effect.source}: relevant set effect uses unsupported operation {effect.operation.value}"

    @classmethod
    def candidate_for_set(
        cls,
        repository: GearSetRepository,
        set_name: str,
        objective_key: str,
        *,
        equipped_piece_count: int | None = None,
        resolver: GearSetEffectResolver | None = None,
    ) -> ExtremeGearSetObjectiveCandidate:
        objective = str(objective_key).strip().casefold()
        target_stats = cls._target_stats(objective)
        gear_set = repository.get_set(set_name)
        if gear_set is None:
            raise KeyError(f"gear set not found: {set_name!r}")

        piece_count = (
            cls._maximum_useful_piece_count(repository, gear_set)
            if equipped_piece_count is None
            else int(equipped_piece_count)
        )
        if piece_count < 0:
            raise ValueError("equipped gear-set piece count must be non-negative")
        if gear_set.max_equip_count is not None and int(gear_set.max_equip_count) > 0:
            if piece_count > int(gear_set.max_equip_count):
                raise ValueError(
                    f"{gear_set.name}: equipped piece count {piece_count} exceeds canonical max "
                    f"{gear_set.max_equip_count}"
                )

        active_bonuses = cls._active_bonuses(repository, gear_set.id, piece_count)
        effect_resolver = resolver or GearSetEffectResolver()
        all_effects: list[Effect] = []
        unresolved: list[str] = []
        reviewed_delta = 0.0

        for bonus in active_bonuses:
            source = f"{gear_set.name} ({bonus.piece_count})"
            effects = tuple(
                effect_resolver.resolve(
                    bonus,
                    use_max_value=True,
                    source=source,
                )
            )
            all_effects.extend(effects)

            if not effects:
                raw_description = str(bonus.description or "").strip()
                description = normalize_eso_markup(raw_description).text.strip()
                if description:
                    if objective in cls._MAX_RESOURCE_OBJECTIVES:
                        screening = ExtremeGearSetResourceObjectiveScreeningService.review(
                            description,
                            objective,
                        )
                        if screening.proven_irrelevant:
                            continue
                    unresolved.append(
                        f"{source}: active set bonus is not yet mechanic-mapped: {description}"
                    )
                continue

            for effect in effects:
                if effect.stat not in target_stats:
                    continue
                contribution, blocker = cls._project_relevant_effect(effect, objective)
                if blocker:
                    unresolved.append(blocker)
                elif contribution is not None:
                    reviewed_delta += float(contribution)

        return ExtremeGearSetObjectiveCandidate(
            set_id=gear_set.id,
            set_name=gear_set.name,
            category=gear_set.category,
            equipped_piece_count=piece_count,
            objective_key=objective,
            reviewed_delta=float(reviewed_delta),
            source_bonuses=active_bonuses,
            source_effects=tuple(all_effects),
            unresolved=tuple(unresolved),
        )

    @classmethod
    def candidates_for_objective(
        cls,
        repository: GearSetRepository,
        objective_key: str,
    ) -> tuple[ExtremeGearSetObjectiveCandidate, ...]:
        cls._target_stats(objective_key)
        rows = tuple(
            cls.candidate_for_set(repository, gear_set.name, objective_key)
            for gear_set in repository.list_sets()
        )
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    not row.mechanic_complete,
                    -row.reviewed_delta,
                    row.set_name.casefold(),
                    row.set_id,
                ),
            )
        )

    @classmethod
    def best_mechanic_complete_single_set_for_objective(
        cls,
        repository: GearSetRepository,
        objective_key: str,
    ) -> ExtremeGearSetObjectiveCandidate | None:
        return next(
            (
                row
                for row in cls.candidates_for_objective(repository, objective_key)
                if row.mechanic_complete
            ),
            None,
        )
