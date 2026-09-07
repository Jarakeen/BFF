from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild, IllegalBuildError
from minmax.character_build.weapon_type import WeaponType
from minmax.heavy_attack_restoration import (
    HeavyAttackWeaponType,
    resource_for_heavy_attack_weapon,
)
from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationHeavyAttackWeaponResolution:
    """Build-derived weapon/resource identity for one scheduled heavy attack."""

    action: RotationAction
    active_bar: str
    weapon: HeavyAttackWeaponType
    resource: ResourceType


@dataclass(frozen=True)
class RotationHeavyAttackWeaponViolation:
    action: RotationAction
    reason: str


@dataclass(frozen=True)
class RotationHeavyAttackWeaponProjection:
    resolutions: tuple[RotationHeavyAttackWeaponResolution, ...]
    violations: tuple[RotationHeavyAttackWeaponViolation, ...]
    unresolved: tuple[str, ...]

    @property
    def is_legal(self) -> bool:
        return not self.violations and not self.unresolved


class RotationHeavyAttackWeaponProjectionService:
    """Resolve each scheduled heavy attack from the build's active weapon bar.

    This service resolves weapon/resource identity only. It deliberately does not
    infer heavy-attack duration, full-charge completion, restoration magnitude,
    passive modifiers, or Werewolf/unarmed transformation state.

    Bar state is reconstructed from the ordered RotationPlan, including same-time
    BAR_SWAP actions through their explicit sequence values. An explicit heavy
    action bar must agree with the reconstructed active bar rather than overriding it.
    """

    def project(
        self,
        *,
        build: CharacterBuild,
        plan: RotationPlan,
        initial_bar: str,
    ) -> RotationHeavyAttackWeaponProjection:
        violations = tuple(build.validate())
        if violations:
            raise IllegalBuildError(violations)

        active_bar = str(initial_bar or "").strip().casefold()
        if active_bar not in {"front", "back"}:
            raise ValueError("rotation heavy-attack initial_bar must be front or back")

        resolutions: list[RotationHeavyAttackWeaponResolution] = []
        projection_violations: list[RotationHeavyAttackWeaponViolation] = []
        unresolved: list[str] = []

        for action in plan.actions:
            if action.kind is RotationActionKind.BAR_SWAP:
                active_bar = str(action.bar)
                continue
            if action.kind is not RotationActionKind.HEAVY_ATTACK:
                continue

            if action.bar is not None and action.bar != active_bar:
                projection_violations.append(
                    RotationHeavyAttackWeaponViolation(
                        action=action,
                        reason=(
                            f"heavy attack claims {action.bar} bar, but the rotation "
                            f"plan has {active_bar} bar active"
                        ),
                    )
                )
                continue

            bar = build.front_bar if active_bar == "front" else build.back_bar
            if bar is None:
                unresolved.append(
                    f"scheduled heavy attack at {action.time_seconds:.3f}s uses "
                    f"{active_bar} bar, but that bar is unavailable on the build"
                )
                continue

            try:
                weapon = self._heavy_weapon_type(
                    main_hand=bar.main_hand.weapon_type,
                    off_hand=(
                        WeaponType.NONE
                        if bar.off_hand is None
                        else bar.off_hand.weapon_type
                    ),
                )
            except ValueError as exc:
                unresolved.append(
                    f"scheduled heavy attack at {action.time_seconds:.3f}s on "
                    f"{active_bar} bar: {exc}"
                )
                continue

            resolutions.append(
                RotationHeavyAttackWeaponResolution(
                    action=action,
                    active_bar=active_bar,
                    weapon=weapon,
                    resource=resource_for_heavy_attack_weapon(weapon),
                )
            )

        return RotationHeavyAttackWeaponProjection(
            resolutions=tuple(resolutions),
            violations=tuple(projection_violations),
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _heavy_weapon_type(
        *,
        main_hand: WeaponType,
        off_hand: WeaponType,
    ) -> HeavyAttackWeaponType:
        one_handed = {
            WeaponType.SWORD,
            WeaponType.AXE,
            WeaponType.MACE,
            WeaponType.DAGGER,
        }
        two_handed = {
            WeaponType.GREATSWORD,
            WeaponType.BATTLEAXE,
            WeaponType.MAUL,
        }

        if main_hand is WeaponType.BOW and off_hand is WeaponType.NONE:
            return HeavyAttackWeaponType.BOW
        if main_hand in two_handed and off_hand is WeaponType.NONE:
            return HeavyAttackWeaponType.TWO_HANDED
        if main_hand in one_handed and off_hand is WeaponType.SHIELD:
            return HeavyAttackWeaponType.ONE_HAND_AND_SHIELD
        if main_hand in one_handed and off_hand in one_handed:
            return HeavyAttackWeaponType.DUAL_WIELD
        if main_hand is WeaponType.FLAME_STAFF and off_hand is WeaponType.NONE:
            return HeavyAttackWeaponType.FIRE_STAFF
        if main_hand is WeaponType.FROST_STAFF and off_hand is WeaponType.NONE:
            return HeavyAttackWeaponType.FROST_STAFF
        if main_hand is WeaponType.LIGHTNING_STAFF and off_hand is WeaponType.NONE:
            return HeavyAttackWeaponType.SHOCK_STAFF
        if main_hand is WeaponType.RESTORATION_STAFF and off_hand is WeaponType.NONE:
            return HeavyAttackWeaponType.RESTORATION_STAFF

        raise ValueError(
            "heavy-attack weapon identity is unsupported for "
            f"main_hand={main_hand.value!r}, off_hand={off_hand.value!r}"
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return tuple(result)


__all__ = [
    "RotationHeavyAttackWeaponProjection",
    "RotationHeavyAttackWeaponProjectionService",
    "RotationHeavyAttackWeaponResolution",
    "RotationHeavyAttackWeaponViolation",
]
