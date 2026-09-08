from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild, IllegalBuildError
from minmax.character_build.weapon_type import WeaponSkillLine, WeaponType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationWeaponAttackResolution:
    """Build-derived weapon identity for one scheduled light or heavy attack."""

    action: RotationAction
    active_bar: str
    weapon_skill_line: WeaponSkillLine
    main_hand: WeaponType
    off_hand: WeaponType


@dataclass(frozen=True)
class RotationWeaponAttackViolation:
    action: RotationAction
    reason: str


@dataclass(frozen=True)
class RotationWeaponAttackProjection:
    resolutions: tuple[RotationWeaponAttackResolution, ...]
    violations: tuple[RotationWeaponAttackViolation, ...]
    unresolved: tuple[str, ...]

    @property
    def is_legal(self) -> bool:
        return not self.violations and not self.unresolved


class RotationWeaponAttackProjectionService:
    """Resolve scheduled weapon attacks against the reconstructed active bar.

    This layer owns only active-bar/weapon identity for LIGHT_ATTACK and
    HEAVY_ATTACK actions. It does not infer whether an attack hit a target, heavy
    completion/channel duration, restoration magnitude, Ultimate generation, or
    transformation/unarmed semantics.
    """

    _ATTACK_KINDS = frozenset(
        {RotationActionKind.LIGHT_ATTACK, RotationActionKind.HEAVY_ATTACK}
    )

    def project(
        self,
        *,
        build: CharacterBuild,
        plan: RotationPlan,
        initial_bar: str,
    ) -> RotationWeaponAttackProjection:
        build_violations = tuple(build.validate())
        if build_violations:
            raise IllegalBuildError(build_violations)

        active_bar = str(initial_bar or "").strip().casefold()
        if active_bar not in {"front", "back"}:
            raise ValueError("rotation weapon-attack initial_bar must be front or back")

        resolutions: list[RotationWeaponAttackResolution] = []
        violations: list[RotationWeaponAttackViolation] = []
        unresolved: list[str] = []

        for action in plan.actions:
            if action.kind is RotationActionKind.BAR_SWAP:
                destination = str(action.bar or "").strip().casefold()
                if destination not in {"front", "back"}:
                    unresolved.append(
                        f"bar swap at {action.time_seconds:.3f}s has unresolved destination "
                        f"{action.bar!r}"
                    )
                    continue
                active_bar = destination
                continue

            if action.kind not in self._ATTACK_KINDS:
                continue

            if action.bar is not None and str(action.bar).casefold() != active_bar:
                violations.append(
                    RotationWeaponAttackViolation(
                        action=action,
                        reason=(
                            f"{action.kind.value.replace('_', ' ')} claims {action.bar} bar, "
                            f"but the rotation plan has {active_bar} bar active"
                        ),
                    )
                )
                continue

            bar = build.front_bar if active_bar == "front" else build.back_bar
            if bar is None:
                unresolved.append(
                    f"scheduled {action.kind.value.replace('_', ' ')} at "
                    f"{action.time_seconds:.3f}s uses {active_bar} bar, but that bar "
                    "is unavailable on the build"
                )
                continue

            off_hand = (
                WeaponType.NONE
                if bar.off_hand is None
                else bar.off_hand.weapon_type
            )
            try:
                weapon_skill_line = bar.weapon_skill_line
            except ValueError as exc:
                unresolved.append(
                    f"scheduled {action.kind.value.replace('_', ' ')} at "
                    f"{action.time_seconds:.3f}s on {active_bar} bar has unresolved "
                    f"weapon identity: {exc}"
                )
                continue

            resolutions.append(
                RotationWeaponAttackResolution(
                    action=action,
                    active_bar=active_bar,
                    weapon_skill_line=weapon_skill_line,
                    main_hand=bar.main_hand.weapon_type,
                    off_hand=off_hand,
                )
            )

        return RotationWeaponAttackProjection(
            resolutions=tuple(resolutions),
            violations=tuple(violations),
            unresolved=self._dedupe(tuple(unresolved)),
        )

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)


__all__ = [
    "RotationWeaponAttackProjection",
    "RotationWeaponAttackProjectionService",
    "RotationWeaponAttackResolution",
    "RotationWeaponAttackViolation",
]
