from __future__ import annotations

"""Explicit whole-catalog descriptor aggregation.

Descriptor-family modules should describe only their own domain. This module is the
single place allowed to concatenate those families for ``SERVICE_CATALOG`` bootstrap.
It is metadata-only and must not instantiate or execute runtime services.
"""

from services.application_catalog_descriptors import APPLICATION_SERVICE_DESCRIPTORS
from services.comp_maker_catalog_descriptors import COMP_MAKER_LOCAL_SERVICE_DESCRIPTORS
from services.extreme_catalog_descriptors import EXTREME_SERVICE_DESCRIPTORS
from services.extreme_health_recovery_catalog_descriptors import (
    EXTREME_HEALTH_RECOVERY_SERVICE_DESCRIPTORS,
)
from services.extreme_recovery_catalog_descriptors import EXTREME_RECOVERY_SERVICE_DESCRIPTORS
from services.extreme_spell_damage_catalog_descriptors import (
    EXTREME_SPELL_DAMAGE_SERVICE_DESCRIPTORS,
)
from services.extreme_weapon_damage_catalog_descriptors import (
    EXTREME_WEAPON_DAMAGE_SERVICE_DESCRIPTORS,
)
from services.raid_plan_catalog_descriptors import RAID_PLAN_SERVICE_DESCRIPTORS
from services.rotation_catalog_descriptors import ROTATION_SERVICE_DESCRIPTORS
from services.rotation_dd_catalog_descriptors import ROTATION_DD_SERVICE_DESCRIPTORS
from services.rotation_dd_periodic_catalog_descriptors import (
    ROTATION_DD_PERIODIC_SERVICE_DESCRIPTORS,
)
from services.rotation_gameplay_policy_catalog_descriptors import (
    ROTATION_GAMEPLAY_POLICY_SERVICE_DESCRIPTORS,
)
from services.rotation_observation_catalog_descriptors import (
    ROTATION_OBSERVATION_SERVICE_DESCRIPTORS,
)
from services.rotation_runtime_integration_catalog_descriptors import (
    ROTATION_RUNTIME_INTEGRATION_SERVICE_DESCRIPTORS,
)
from services.rotation_tank_catalog_descriptors import ROTATION_TANK_SERVICE_DESCRIPTORS
from services.rotation_tank_integration_catalog_descriptors import (
    ROTATION_TANK_INTEGRATION_SERVICE_DESCRIPTORS,
)
from services.team_prescription_catalog_descriptors import (
    TEAM_PRESCRIPTION_SERVICE_DESCRIPTORS,
)
from services.team_provider_catalog_descriptors import TEAM_PROVIDER_SERVICE_DESCRIPTORS
from services.team_workflow_catalog_descriptors import TEAM_WORKFLOW_SERVICE_DESCRIPTORS


ALL_EXTENSION_SERVICE_DESCRIPTORS = (
    *APPLICATION_SERVICE_DESCRIPTORS,
    *COMP_MAKER_LOCAL_SERVICE_DESCRIPTORS,
    *RAID_PLAN_SERVICE_DESCRIPTORS,
    *EXTREME_SERVICE_DESCRIPTORS,
    *EXTREME_HEALTH_RECOVERY_SERVICE_DESCRIPTORS,
    *EXTREME_RECOVERY_SERVICE_DESCRIPTORS,
    *EXTREME_SPELL_DAMAGE_SERVICE_DESCRIPTORS,
    *EXTREME_WEAPON_DAMAGE_SERVICE_DESCRIPTORS,
    *ROTATION_SERVICE_DESCRIPTORS,
    *ROTATION_DD_SERVICE_DESCRIPTORS,
    *ROTATION_DD_PERIODIC_SERVICE_DESCRIPTORS,
    *ROTATION_GAMEPLAY_POLICY_SERVICE_DESCRIPTORS,
    *ROTATION_OBSERVATION_SERVICE_DESCRIPTORS,
    *ROTATION_RUNTIME_INTEGRATION_SERVICE_DESCRIPTORS,
    *ROTATION_TANK_SERVICE_DESCRIPTORS,
    *ROTATION_TANK_INTEGRATION_SERVICE_DESCRIPTORS,
    *TEAM_PRESCRIPTION_SERVICE_DESCRIPTORS,
    *TEAM_PROVIDER_SERVICE_DESCRIPTORS,
    *TEAM_WORKFLOW_SERVICE_DESCRIPTORS,
)


__all__ = ["ALL_EXTENSION_SERVICE_DESCRIPTORS"]
