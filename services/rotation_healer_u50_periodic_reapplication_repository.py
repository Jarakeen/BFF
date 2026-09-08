from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RotationHealerPeriodicReapplicationKind(str, Enum):
    """Reviewed topology for what another cast/activation is allowed to do.

    These values deliberately stop short of inventing the exact timestamp at
    which the old periodic effect stops or the new one begins. They answer only
    the higher-level topology question needed before a generic RESTART policy can
    be considered legal.
    """

    SECOND_ACTIVATION_SPECIAL = "second_activation_special"
    ONE_ACTIVE_INSTANCE = "one_active_instance"


@dataclass(frozen=True)
class RotationHealerReviewedReapplicationEvidence:
    source_name: str
    coefficient_number: int
    kind: RotationHealerPeriodicReapplicationKind
    provenance: tuple[str, ...]
    note: str


class RotationHealerU50PeriodicReapplicationRepository:
    """Reviewed U50 reapplication topology for healer periodic components.

    This repository does not supply a refresh policy. A source saying "only one
    active" proves that overlap is constrained, but it does not by itself prove
    the exact old-effect termination boundary. Budding Seeds is even more
    specific: activating the skill again while the field is active causes the
    delayed bloom, so a second activation must not be modeled as a generic HoT
    restart.
    """

    _REVIEWED: dict[
        tuple[str, int], RotationHealerReviewedReapplicationEvidence
    ] = {
        ("budding seeds", 2): RotationHealerReviewedReapplicationEvidence(
            source_name="Budding Seeds",
            coefficient_number=2,
            kind=RotationHealerPeriodicReapplicationKind.SECOND_ACTIVATION_SPECIAL,
            provenance=(
                "current U50 Budding Seeds tooltip: activating the ability again causes the field to instantly bloom",
                "current U50 tooltip separately states the field grows for 6 seconds and heals every 1 second while growing",
            ),
            note=(
                "a second activation during the active field is a bloom trigger, not "
                "evidence of a generic periodic restart"
            ),
        ),
        ("illustrious healing", 1): RotationHealerReviewedReapplicationEvidence(
            source_name="Illustrious Healing",
            coefficient_number=1,
            kind=RotationHealerPeriodicReapplicationKind.ONE_ACTIVE_INSTANCE,
            provenance=(
                "ZOS Update 23 Grand Healing patch notes: the ability and its morphs may have only 1 active instance at a time",
                "Illustrious Healing is the duration-extending Grand Healing morph",
            ),
            note=(
                "one-active-instance topology is verified, but the exact old-field "
                "termination/replacement boundary is still unresolved"
            ),
        ),
        ("energy orb", 1): RotationHealerReviewedReapplicationEvidence(
            source_name="Energy Orb",
            coefficient_number=1,
            kind=RotationHealerPeriodicReapplicationKind.ONE_ACTIVE_INSTANCE,
            provenance=(
                "ZOS Update 23 Necrotic Orb patch notes: only 1 orb may be active at a time",
                "Energy Orb is the healing morph of Necrotic Orb",
            ),
            note=(
                "one-active-orb topology is verified, but the exact replacement/despawn "
                "boundary on recast is still unresolved"
            ),
        ),
    }

    def get(
        self,
        *,
        source_name: str,
        coefficient_number: int,
    ) -> RotationHealerReviewedReapplicationEvidence | None:
        key = (str(source_name or "").strip().casefold(), int(coefficient_number))
        return self._REVIEWED.get(key)
