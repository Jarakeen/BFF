from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from engine.config import get_data_dir
from minmax.build_candidate_damage import calculation_result_from_build_context
from minmax.build_evaluation import BuildEvaluation
from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_layer import BarId
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.combat_contribution import CombatContribution
from models.build_model import GearSlot, PlayerBuild
from services.rotation_static_build_context_service import RotationStaticBuildContextResolution


_WEAPON_TYPE_BY_NAME = {
    "bow": WeaponType.BOW,
    "inferno staff": WeaponType.FLAME_STAFF,
    "fire staff": WeaponType.FLAME_STAFF,
    "flame staff": WeaponType.FLAME_STAFF,
    "lightning staff": WeaponType.LIGHTNING_STAFF,
    "shock staff": WeaponType.LIGHTNING_STAFF,
    "ice staff": WeaponType.FROST_STAFF,
    "frost staff": WeaponType.FROST_STAFF,
    "restoration staff": WeaponType.RESTORATION_STAFF,
    "sword": WeaponType.SWORD,
    "axe": WeaponType.AXE,
    "mace": WeaponType.MACE,
    "dagger": WeaponType.DAGGER,
    "shield": WeaponType.SHIELD,
}

# Legacy saved builds may retain only the weapon *family*. This representative is
# permitted only inside the isolated LA/HA weapon-attack bridge. UESP's preserved
# LAOneHand/LATwoHand equations and the canonical HA routing are family-level here,
# so no subtype-specific passive, trait, enchant, or penetration mechanic is inferred.
_LEGACY_ATTACK_FAMILY_REPRESENTATIVE_BY_NAME = {
    "two-handed": WeaponType.GREATSWORD,
    "two handed": WeaponType.GREATSWORD,
}


@dataclass(frozen=True)
class RotationWeaponAttackBuildEvaluationResolution:
    """Canonical weapon-only build plus bar-specific attack evaluations."""

    build: CharacterBuild | None
    evaluations: tuple[tuple[str, BuildEvaluation], ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.build is not None and bool(self.evaluations) and not self.unresolved

    def evaluation_for(self, bar: str) -> BuildEvaluation | None:
        key = str(bar or "").strip().casefold()
        for candidate_bar, evaluation in self.evaluations:
            if candidate_bar == key:
                return evaluation
        return None


class RotationSavedBuildWeaponAttackContributionService:
    """Resolve reviewed saved-build modifier buckets used by LA/HA formulas.

    The canonical weapon-attack calculators consume historical ``CombatContribution``
    buckets. This adapter maps only saved-build Champion Point facts whose semantics are
    explicit and reviewed. It does not infer uptime or synthesize unknown modifier
    families.
    """

    _WEAPONS_EXPERT_THRESHOLDS = (10, 20, 30, 40, 50)
    _WEAPONS_EXPERT_PER_STAGE = 0.04
    _MASTER_AT_ARMS_THRESHOLDS = (25, 50)
    _MASTER_AT_ARMS_PER_STAGE = 0.03
    _DEADLY_AIM_THRESHOLDS = (25, 50)
    _DEADLY_AIM_PER_STAGE = 0.03

    @staticmethod
    def _key(value: object) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _points(value: object) -> int | None:
        try:
            points = int(str(value or "0").strip() or "0")
        except (TypeError, ValueError):
            return None
        return points if points >= 0 else None

    @staticmethod
    def _stages(points: int, thresholds: tuple[int, ...]) -> int:
        return sum(1 for threshold in thresholds if points >= threshold)

    @staticmethod
    def _contribution(source: str, effect_type: str, value: float) -> CombatContribution:
        return CombatContribution(
            source=source,
            effect_type=effect_type,
            raw_value=float(value),
            uptime=1.0,
            effective_value=float(value),
        )

    def resolve(
        self,
        build: PlayerBuild,
    ) -> tuple[tuple[CombatContribution, ...], tuple[str, ...]]:
        contributions: list[CombatContribution] = []
        unresolved: list[str] = []

        for entry in tuple(getattr(build, "ChampionPoints", ()) or ()):
            name = str(getattr(entry, "Name", "") or "").strip()
            if not name:
                continue
            key = self._key(name)
            if key not in {"weapons expert", "master-at-arms", "deadly aim"}:
                continue

            points = self._points(getattr(entry, "Points", ""))
            if points is None:
                unresolved.append(
                    f"Champion Point {name}: allocation is not a non-negative integer"
                )
                continue

            if key == "weapons expert":
                stages = self._stages(points, self._WEAPONS_EXPERT_THRESHOLDS)
                value = stages * self._WEAPONS_EXPERT_PER_STAGE
                if value:
                    source = f"Champion Point: Weapons Expert ({points} points)"
                    contributions.append(self._contribution(source, "cp_la_damage", value))
                    contributions.append(self._contribution(source, "cp_ha_damage", value))
                continue

            if key == "master-at-arms":
                stages = self._stages(points, self._MASTER_AT_ARMS_THRESHOLDS)
                value = stages * self._MASTER_AT_ARMS_PER_STAGE
                if value:
                    contributions.append(
                        self._contribution(
                            f"Champion Point: Master-at-Arms ({points} points)",
                            "direct_damage_done",
                            value,
                        )
                    )
                continue

            stages = self._stages(points, self._DEADLY_AIM_THRESHOLDS)
            value = stages * self._DEADLY_AIM_PER_STAGE
            if value:
                contributions.append(
                    self._contribution(
                        f"Champion Point: Deadly Aim ({points} points)",
                        "single_target_damage_done",
                        value,
                    )
                )

        return tuple(contributions), tuple(dict.fromkeys(unresolved))


class RotationSavedBuildWeaponAttackEvaluationService:
    """Bridge saved-build static contexts into LA/HA evaluation evidence.

    Static stats remain owned by ``RotationStaticBuildContextService``. The broad
    ``SavedBuildCharacterAdapter`` is still used for canonical character metadata,
    but weapon attacks deliberately rebuild a weapon-only bar surface from the saved
    main/off-hand weapon evidence. Skill legality, weapon-enchantment label
    resolution, and other unrelated canonical-build concerns must not veto a basic
    LA/HA.

    Exact weapon identities are preferred. The legacy aggregate ``Two-Handed`` label
    is accepted only in this isolated weapon-attack bridge because the preserved
    LAOneHand/LATwoHand arithmetic and canonical HA routing are family-level. A
    concrete two-handed subtype is used only as an internal carrier here; it is not
    promoted into saved build state and cannot establish subtype-specific mechanics.
    Other ambiguous aggregate labels remain unresolved.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        build_adapter: SavedBuildCharacterAdapter | None = None,
        contribution_service: RotationSavedBuildWeaponAttackContributionService | None = None,
    ) -> None:
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else get_data_dir() / "eso.db"
        )
        self.build_adapter = build_adapter or SavedBuildCharacterAdapter(self.database_path)
        self.contribution_service = (
            contribution_service or RotationSavedBuildWeaponAttackContributionService()
        )

    @staticmethod
    def _conditional_exploiter_contribution(value: float) -> CombatContribution | None:
        bonus = max(0.0, float(value))
        if bonus <= 0.0:
            return None
        return CombatContribution(
            source="Champion Point: Exploiter runtime magnitude",
            effect_type="conditional_exploiter_damage_done",
            raw_value=bonus,
            uptime=1.0,
            effective_value=bonus,
        )

    @staticmethod
    def _weapon_type(slot: GearSlot) -> WeaponType | None:
        if slot.is_empty:
            return None
        key = " ".join(str(slot.WeaponType or "").strip().casefold().split())
        exact = _WEAPON_TYPE_BY_NAME.get(key)
        if exact is not None:
            return exact
        return _LEGACY_ATTACK_FAMILY_REPRESENTATIVE_BY_NAME.get(key)

    @staticmethod
    def _placeholder_slots(bar: str) -> tuple[SlottedSkill, ...]:
        return tuple(
            SlottedSkill(
                skill_id=f"rotation_weapon_attack_{bar}_slot_{index + 1}",
                skill_line_id="rotation_weapon_attack",
                is_ultimate=(index == 5),
                is_cast=False,
                requires_active_bar=True,
            )
            for index in range(6)
        )

    @classmethod
    def _weapon_only_bar(
        cls,
        build: PlayerBuild,
        bar: str,
    ) -> Bar | None:
        main_slot, off_slot = build.active_weapon_slots(bar)
        main_type = cls._weapon_type(main_slot)
        if main_type is None:
            return None

        off_type = cls._weapon_type(off_slot)
        if not off_slot.is_empty and off_type is None:
            return None

        bar_id = BarId.FRONT if bar == "front" else BarId.BACK
        candidate = Bar(
            bar_id=bar_id,
            main_hand=Weapon(weapon_type=main_type),
            off_hand=(None if off_type is None else Weapon(weapon_type=off_type)),
            slots=cls._placeholder_slots(bar),
        )
        return candidate if not candidate.violations() else None

    @classmethod
    def _weapon_only_build(
        cls,
        canonical: CharacterBuild,
        saved: PlayerBuild,
    ) -> CharacterBuild:
        return replace(
            canonical,
            front_bar=cls._weapon_only_bar(saved, "front"),
            back_bar=cls._weapon_only_bar(saved, "back"),
        )

    def resolve(
        self,
        *,
        player_build: PlayerBuild,
        static_context: RotationStaticBuildContextResolution,
    ) -> RotationWeaponAttackBuildEvaluationResolution:
        if not static_context.resolved:
            detail = tuple(static_context.unresolved) or (
                "canonical static build context is unresolved",
            )
            return RotationWeaponAttackBuildEvaluationResolution(
                build=None,
                unresolved=detail,
            )

        character_id = str(
            getattr(static_context.progression, "character_id", "") or ""
        ).strip() or None
        adaptation = self.build_adapter.adapt(
            player_build,
            character_id=character_id,
        )
        if adaptation.build is None:
            return RotationWeaponAttackBuildEvaluationResolution(
                build=None,
                unresolved=tuple(adaptation.unresolved) or (
                    "canonical saved-build character metadata is unavailable",
                ),
            )

        weapon_build = self._weapon_only_build(adaptation.build, player_build)
        contributions, contribution_unresolved = self.contribution_service.resolve(
            player_build
        )
        unresolved = list(contribution_unresolved)
        evaluations: list[tuple[str, BuildEvaluation]] = []

        for context in static_context.contexts:
            calculation = calculation_result_from_build_context(context)
            if calculation is None:
                unresolved.append(
                    f"{context.active_bar} weapon-attack evaluation requires resolved canonical core stats"
                )
                continue
            conditional = self._conditional_exploiter_contribution(
                getattr(context, "dd_exploiter_bonus", 0.0)
            )
            context_contributions = (
                contributions
                if conditional is None
                else (*contributions, conditional)
            )
            evaluations.append(
                (
                    context.active_bar,
                    BuildEvaluation(
                        stats=calculation,
                        combat_effects=(),
                        combat_contributions=context_contributions,
                    ),
                )
            )

        return RotationWeaponAttackBuildEvaluationResolution(
            build=weapon_build,
            evaluations=tuple(evaluations),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationSavedBuildWeaponAttackContributionService",
    "RotationSavedBuildWeaponAttackEvaluationService",
    "RotationWeaponAttackBuildEvaluationResolution",
]
