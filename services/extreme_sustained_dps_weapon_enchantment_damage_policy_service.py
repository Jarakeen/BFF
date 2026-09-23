from __future__ import annotations

"""Verified policy semantics for selected weapon-enchantment damage consequences."""

from dataclasses import dataclass
import math

from minmax.proc_critical_eligibility import (
    ProcDamageKind,
    ProcScalingKind,
    resolve_proc_critical_eligibility,
)
from services.extreme_sustained_dps_weapon_enchantment_proc_consequence_service import (
    ExtremeSustainedDPSWeaponEnchantmentProcOccurrence,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentDamageConsequence:
    time_seconds: float
    sequence: int
    source_label: str
    damage_type: str
    raw_value: float
    can_crit: bool | None
    critical_evidence: str


@dataclass(frozen=True)
class ExtremeSustainedDPSWeaponEnchantmentDamagePolicyResolution:
    consequences: tuple[ExtremeSustainedDPSWeaponEnchantmentDamageConsequence, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class ExtremeSustainedDPSWeaponEnchantmentDamagePolicyService:
    """Project only reviewed damage semantics from exact selected glyph procs."""

    pass
