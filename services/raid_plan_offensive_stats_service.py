from __future__ import annotations

"""Raid-plan Critical Damage and Penetration projection.

This service composes canonical per-build standing stats with explicit/planned
raid-wide support evidence. It deliberately keeps personal penetration,
target-side Armor reduction, and target Critical Damage Taken separate so the
UI can show the math instead of collapsing unlike mechanics into one number.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from engine.config import DEFAULT_DATABASE, get_data_dir
from minmax.gear_set_repository import GearSetRepository
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from minmax.race_repository import RaceRepository
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan
from services.build_service import BuildService
from services.build_profile_service import BuildProfileService, build_with_effective_item_profile
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter
from services.raid_plan_saved_build_resolution_service import RaidPlanSavedBuildResolutionService
from services.saved_build_capability_service import SavedBuildCapabilityService


PVE_TARGET_RESISTANCE = 18_200.0
CRITICAL_DAMAGE_CAP = 1.25

_NAMED_CRIT_DAMAGE = {
    "Minor Force": 0.10,
    "Major Force": 0.20,
}
_TARGET_CRIT_DAMAGE_TAKEN = {
    "Minor Brittle": 0.10,
    "Major Brittle": 0.20,
}
_FIXED_TARGET_RESISTANCE_REDUCTION = {
    "Minor Breach": 2974.0,
    "Major Breach": 5948.0,
}


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: object) -> str:
    return _clean(value).casefold()


@dataclass(frozen=True)
class RaidOffensiveStatContribution:
    label: str
    value: float
    kind: str
    conditional: bool = False


@dataclass(frozen=True)
class RaidPlanOffensiveStatRow:
    seat_id: str
    player_label: str
    eso_class: str
    personal_critical_damage: float | None
    raid_critical_damage: float | None
    physical_penetration: float | None
    spell_penetration: float | None
    raid_armor_reduction: float
    effective_physical_penetration: float | None
    effective_spell_penetration: float | None
    physical_overpenetration: float | None
    spell_overpenetration: float | None
    critical_capped: bool
    contributions: tuple[RaidOffensiveStatContribution, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return (
            self.personal_critical_damage is not None
            and self.physical_penetration is not None
            and self.spell_penetration is not None
        )


@dataclass(frozen=True)
class RaidPlanOffensiveStats:
    plan_id: str
    target_resistance: float
    raid_armor_reduction: float
    rows: tuple[RaidPlanOffensiveStatRow, ...]
    raid_contributions: tuple[RaidOffensiveStatContribution, ...] = ()
    unresolved: tuple[str, ...] = ()


class RaidPlanOffensiveStatsService:
    """Calculate per-seat Critical Damage and Penetration for a saved Raid Plan."""

    def __init__(
        self,
        *,
        database_path: Path | None = None,
        build_service: BuildService | None = None,
        context_factory=None,
        capability_service: SavedBuildCapabilityService | None = None,
        resolver: RaidPlanSavedBuildResolutionService | None = None,
        profile_service: BuildProfileService | None = None,
    ) -> None:
        self.database_path = Path(database_path or DEFAULT_DATABASE)
        self.build_service = build_service or BuildService(get_data_dir() / "builds.json")
        self.context_factory = context_factory or Phase5BuildCalculationContextFactory(
            race_repository=RaceRepository(self.database_path),
            gear_set_repository=GearSetRepository(self.database_path),
        )
        self.progression = MinmaxCharacterProgressionAdapter(
            self.build_service.canonical.catalog_service
        )
        self.capabilities = capability_service or SavedBuildCapabilityService(
            self.build_service,
            self.database_path,
        )
        self.resolver = resolver or RaidPlanSavedBuildResolutionService()
        self.profile_service = profile_service or BuildProfileService(get_data_dir() / "build_profiles.json")

    @staticmethod
    def _trace_contributions(trace, kind: str) -> tuple[RaidOffensiveStatContribution, ...]:
        if trace is None:
            return ()
        rows: list[RaidOffensiveStatContribution] = []
        for label, operation, value, _result in tuple(getattr(trace, "steps", ()) or ()):
            label = _clean(label)
            if not label or label in {"base", "ESO rounding", "ESO ratio"}:
                continue
            if operation == "multiply":
                # Preserve trace visibility without pretending a multiplier is a flat delta.
                rows.append(RaidOffensiveStatContribution(label, float(value), f"{kind}:multiplier"))
            else:
                rows.append(RaidOffensiveStatContribution(label, float(value), kind))
        return tuple(rows)

    @staticmethod
    def _explicit_plan_effects(raid_plan: RaidPlan) -> set[str]:
        values: set[str] = set()
        known = {
            *(_NAMED_CRIT_DAMAGE.keys()),
            *(_TARGET_CRIT_DAMAGE_TAKEN.keys()),
            *(_FIXED_TARGET_RESISTANCE_REDUCTION.keys()),
        }
        by_key = {_key(value): value for value in known}
        for member in raid_plan.members:
            for raw in (
                member.primary_assignment,
                member.secondary_assignment,
                *(member.utility_assignments or ()),
                *(member.planned_skills or ()),
            ):
                key = _key(raw)
                if key in by_key:
                    values.add(by_key[key])
                # Aggressive Horn is the common planned source for Major Force.
                if "aggressive horn" in key or key == "war horn":
                    values.add("Major Force")
        return values

    @staticmethod
    def _build_set_names(build: PlayerBuild) -> set[str]:
        names: set[str] = set()
        for entry in build.Armor.values():
            for field in ("Set", "Set2"):
                value = _clean(entry.get(field, ""))
                if value:
                    names.add(value)
        for slot in (
            build.FrontBarWeapon,
            build.FrontBarOffHand,
            build.BackBarWeapon,
            build.BackBarOffHand,
            build.Necklace,
            build.Ring1,
            build.Ring2,
        ):
            for value in (_clean(slot.Set), _clean(slot.Set2)):
                if value:
                    names.add(value)
        for value in getattr(build, "PlannedGearSets", ()) or ():
            value = _clean(value)
            if value:
                names.add(value)
        return names

    def _raid_effects(
        self,
        raid_plan: RaidPlan,
        resolved_builds: Iterable[tuple[str, PlayerBuild]],
    ) -> tuple[
        set[str],
        float,
        tuple[RaidOffensiveStatContribution, ...],
        tuple[str, ...],
        set[str],
    ]:
        named = self._explicit_plan_effects(raid_plan)
        armor_reductions: dict[str, float] = {}
        contributions: list[RaidOffensiveStatContribution] = []
        unresolved: list[str] = []
        lucent_wearers: set[str] = set()

        for seat_id, build in resolved_builds:
            sets = self._build_set_names(build)
            if any(_key(name) == "lucent echoes" for name in sets):
                lucent_wearers.add(_key(seat_id))

            try:
                audit = self.capabilities.audit_build(build)
            except Exception as exc:
                unresolved.append(f"{seat_id}: capability audit failed: {exc}")
                continue

            for effect in audit.resolved_effects:
                effect_name = _clean(getattr(effect, "name", ""))
                target = _key(
                    getattr(
                        getattr(effect, "target_type", None),
                        "value",
                        getattr(effect, "target_type", ""),
                    )
                )
                canonical = next(
                    (
                        name
                        for name in (
                            *_NAMED_CRIT_DAMAGE,
                            *_TARGET_CRIT_DAMAGE_TAKEN,
                            *_FIXED_TARGET_RESISTANCE_REDUCTION,
                        )
                        if _key(name) == _key(effect_name)
                    ),
                    None,
                )
                if canonical in _NAMED_CRIT_DAMAGE and target == "group":
                    named.add(canonical)
                elif canonical in _TARGET_CRIT_DAMAGE_TAKEN and target == "enemy":
                    named.add(canonical)
                elif canonical in _FIXED_TARGET_RESISTANCE_REDUCTION and target == "enemy":
                    named.add(canonical)

                reduction = getattr(effect, "resistance_reduction", None)
                scaling = _clean(getattr(effect, "scaling", ""))
                if reduction is None or float(reduction) <= 0 or target != "enemy":
                    continue
                source = _clean(getattr(effect, "source", "")) or effect_name or "Target Armor reduction"
                if scaling:
                    unresolved.append(
                        f"{seat_id}: {source} has runtime scaling ({scaling}); max value was not assumed"
                    )
                    continue
                key = _key(effect_name or source)
                armor_reductions[key] = max(float(reduction), armor_reductions.get(key, 0.0))

            unresolved.extend(
                f"{seat_id}: {message}"
                for message in audit.capability_unresolved
                if "resistance" in message.casefold() or "critical" in message.casefold()
            )

        for name, value in _FIXED_TARGET_RESISTANCE_REDUCTION.items():
            if name in named:
                armor_reductions[_key(name)] = max(
                    value, armor_reductions.get(_key(name), 0.0)
                )

        for name in sorted(named):
            if name in _NAMED_CRIT_DAMAGE:
                contributions.append(
                    RaidOffensiveStatContribution(name, _NAMED_CRIT_DAMAGE[name], "raid_critical_damage")
                )
            elif name in _TARGET_CRIT_DAMAGE_TAKEN:
                contributions.append(
                    RaidOffensiveStatContribution(
                        name,
                        _TARGET_CRIT_DAMAGE_TAKEN[name],
                        "target_critical_damage_taken",
                    )
                )

        for key, value in sorted(armor_reductions.items()):
            contributions.append(
                RaidOffensiveStatContribution(
                    key,
                    value,
                    "target_resistance_reduction",
                    conditional=key not in {_key(x) for x in _FIXED_TARGET_RESISTANCE_REDUCTION},
                )
            )

        return (
            named,
            sum(armor_reductions.values()),
            tuple(contributions),
            tuple(dict.fromkeys(unresolved)),
            lucent_wearers,
        )

    def calculate(
        self,
        raid_plan: RaidPlan,
        *,
        saved_builds: Iterable[PlayerBuild] | None = None,
        target_resistance: float = PVE_TARGET_RESISTANCE,
        active_bar: str = "front",
    ) -> RaidPlanOffensiveStats:
        if not isinstance(raid_plan, RaidPlan):
            raise TypeError("raid offensive stats require RaidPlan")
        target = float(target_resistance)
        if target < 0:
            raise ValueError("target resistance cannot be negative")

        saved = tuple(
            saved_builds
            if saved_builds is not None
            else self.build_service.load().Members
        )

        resolved: list[tuple[str, PlayerBuild]] = []
        resolution_gaps: dict[str, tuple[str, ...]] = {}
        for member in raid_plan.members:
            result = self.resolver.resolve(
                raid_plan=raid_plan,
                seat_id=member.seat_id,
                saved_builds=saved,
            )
            if result.resolved and result.build is not None:
                resolved.append((member.seat_id, result.build))
            else:
                resolution_gaps[member.seat_id] = tuple(result.unresolved)

        named, raid_reduction, raid_contributions, raid_unresolved, lucent_wearers = (
            self._raid_effects(raid_plan, resolved)
        )

        rows: list[RaidPlanOffensiveStatRow] = []
        by_seat = {_key(seat): build for seat, build in resolved}
        for member in raid_plan.members:
            seat_key = _key(member.seat_id)
            player_label = member.character_name or member.gamertag or member.seat_id
            build = by_seat.get(seat_key)
            if build is None:
                rows.append(
                    RaidPlanOffensiveStatRow(
                        seat_id=member.seat_id,
                        player_label=player_label,
                        eso_class=_clean(member.eso_class),
                        personal_critical_damage=None,
                        raid_critical_damage=None,
                        physical_penetration=None,
                        spell_penetration=None,
                        raid_armor_reduction=raid_reduction,
                        effective_physical_penetration=None,
                        effective_spell_penetration=None,
                        physical_overpenetration=None,
                        spell_overpenetration=None,
                        critical_capped=False,
                        unresolved=resolution_gaps.get(member.seat_id, ("Build unresolved",)),
                    )
                )
                continue

            unresolved: list[str] = []
            contributions: list[RaidOffensiveStatContribution] = []
            progression = self.progression.resolve(build)
            unresolved.extend(progression.unresolved)
            try:
                calculation_build = build_with_effective_item_profile(
                    build,
                    self.profile_service.get(_clean(getattr(build, "BuildId", ""))),
                )
                context = self.context_factory.build(
                    character_id=progression.character_id or member.character_id or member.seat_id,
                    build_id=_clean(getattr(build, "BuildId", "")) or build.BuildName or member.seat_id,
                    build=calculation_build,
                    progression=progression.progression,
                    active_bar=active_bar,
                )
                unresolved.extend(tuple(context.unresolved_gear_effects))
                crit_trace = context.core_state.derived.get(StatId.CRITICAL_DAMAGE)
                physical_trace = context.core_state.derived.get(StatId.PHYSICAL_PENETRATION)
                spell_trace = context.core_state.derived.get(StatId.SPELL_PENETRATION)
                personal_crit = float(crit_trace.final_value) if crit_trace is not None else None
                physical = float(physical_trace.final_value) if physical_trace is not None else None
                spell = float(spell_trace.final_value) if spell_trace is not None else None
                contributions.extend(self._trace_contributions(crit_trace, "personal_critical_damage"))
                contributions.extend(self._trace_contributions(physical_trace, "physical_penetration"))
                contributions.extend(self._trace_contributions(spell_trace, "spell_penetration"))
            except Exception as exc:
                personal_crit = physical = spell = None
                unresolved.append(f"Static offensive stat calculation failed: {exc}")

            raid_crit_bonus = sum(
                _NAMED_CRIT_DAMAGE[name]
                for name in _NAMED_CRIT_DAMAGE
                if name in named
            )
            target_crit_bonus = sum(
                _TARGET_CRIT_DAMAGE_TAKEN[name]
                for name in _TARGET_CRIT_DAMAGE_TAKEN
                if name in named
            )
            # Lucent Echoes is a group-member bonus that excludes the wearer.
            if lucent_wearers and seat_key not in lucent_wearers:
                raid_crit_bonus += 0.11
                contributions.append(
                    RaidOffensiveStatContribution(
                        "Lucent Echoes (group member)",
                        0.11,
                        "raid_critical_damage",
                        conditional=True,
                    )
                )

            contributions.extend(raid_contributions)
            combined_crit = (
                None
                if personal_crit is None
                else min(CRITICAL_DAMAGE_CAP, personal_crit + raid_crit_bonus + target_crit_bonus)
            )
            effective_physical = None if physical is None else physical + raid_reduction
            effective_spell = None if spell is None else spell + raid_reduction
            physical_over = None if effective_physical is None else effective_physical - target
            spell_over = None if effective_spell is None else effective_spell - target

            rows.append(
                RaidPlanOffensiveStatRow(
                    seat_id=member.seat_id,
                    player_label=player_label,
                    eso_class=_clean(member.eso_class or build.EsoClass),
                    personal_critical_damage=personal_crit,
                    raid_critical_damage=combined_crit,
                    physical_penetration=physical,
                    spell_penetration=spell,
                    raid_armor_reduction=raid_reduction,
                    effective_physical_penetration=effective_physical,
                    effective_spell_penetration=effective_spell,
                    physical_overpenetration=physical_over,
                    spell_overpenetration=spell_over,
                    critical_capped=combined_crit is not None and combined_crit >= CRITICAL_DAMAGE_CAP - 1e-9,
                    contributions=tuple(contributions),
                    unresolved=tuple(dict.fromkeys(message for message in unresolved if _clean(message))),
                )
            )

        return RaidPlanOffensiveStats(
            plan_id=raid_plan.plan_id,
            target_resistance=target,
            raid_armor_reduction=raid_reduction,
            rows=tuple(rows),
            raid_contributions=raid_contributions,
            unresolved=raid_unresolved,
        )


__all__ = [
    "CRITICAL_DAMAGE_CAP",
    "PVE_TARGET_RESISTANCE",
    "RaidOffensiveStatContribution",
    "RaidPlanOffensiveStatRow",
    "RaidPlanOffensiveStats",
    "RaidPlanOffensiveStatsService",
]
