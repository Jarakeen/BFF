from __future__ import annotations

"""Corrected entry point for same-build Weapon Damage resource tightening.

The underlying reduced resource audit is mechanically sound, but its shared
resource-warning reconciler originally neutralized only armor-base CP160/Gold
metadata. Exact named-set witnesses can also leave front/back weapon level and
quality unset. Weapon base power cannot modify Max Magicka or Max Stamina, so
those exact metadata-only warnings are equally irrelevant to resource scoring.

This wrapper changes no stat arithmetic, set semantics, database state, or proof
bounds. It monkey-patches only the imported audit-local reconciler before running
the existing tightening audit. Any other unresolved warning still fails closed.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.audit_extreme_weapon_damage_same_build_resource_tightening as tightening


_RESOURCE_OBJECTIVES = ("max_magicka", "max_stamina")
_ARMOR_BASE_WARNING = re.compile(
    r"^(Head|Shoulders|Chest|Hands|Waist|Legs|Feet) armor base: "
    r"CP160 Gold required \(level unset, quality unset\)$"
)
_WEAPON_BASE_WARNING = re.compile(
    r"^(Front Bar|Back Bar) weapon base: "
    r"CP160 Gold required \(level unset, quality unset\)$"
)


def _reconcile_resource_unresolved(
    objective_key: str,
    unresolved: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Neutralize only base-item metadata irrelevant to max-resource objectives."""

    objective = str(objective_key or "").strip().casefold()
    effective: list[str] = []
    neutralized: list[str] = []
    for raw in unresolved:
        message = str(raw or "").strip()
        if not message:
            continue
        metadata_only = (
            _ARMOR_BASE_WARNING.fullmatch(message)
            or _WEAPON_BASE_WARNING.fullmatch(message)
        )
        if objective in _RESOURCE_OBJECTIVES and metadata_only:
            neutralized.append(message)
            continue
        effective.append(message)
    return tuple(dict.fromkeys(effective)), tuple(dict.fromkeys(neutralized))


def main() -> int:
    tightening._reconcile_resource_unresolved = _reconcile_resource_unresolved
    return tightening.main()


if __name__ == "__main__":
    raise SystemExit(main())
