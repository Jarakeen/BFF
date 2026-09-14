from pathlib import Path

from minmax.base_character_state import BASE_STAMINA_RECOVERY
from minmax.combat_effect_semantics import GameUpdate
from minmax.mundus_repository import MundusRepository
from minmax.potion_availability_repository import PotionAvailabilityRepository
from services.extreme_armor_mundus_joint_objective_service import (
    ExtremeArmorMundusJointObjectiveService,
)
from services.extreme_recovery_potion_projection_service import (
    ExtremeRecoveryPotionProjectionService,
)
from services.extreme_recovery_provisioning_projection_service import (
    ExtremeRecoveryProvisioningProjectionService,
)


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "eso.db"
OBJECTIVE = "stamina_recovery"


def test_shared_recovery_services_support_stamina_recovery() -> None:
    provisioning = ExtremeRecoveryProvisioningProjectionService.build(
        DATABASE,
        objective_key=OBJECTIVE,
    )
    potion = ExtremeRecoveryPotionProjectionService(
        PotionAvailabilityRepository(DATABASE, game_update=GameUpdate.U50)
    ).build(OBJECTIVE)
    armor_mundus = ExtremeArmorMundusJointObjectiveService.best_for_objective(
        MundusRepository(DATABASE, initialize=False),
        OBJECTIVE,
        reference_value=BASE_STAMINA_RECOVERY,
    )

    assert provisioning.comparison_proven is True
    assert potion.denominator_proven is True
    assert potion.unresolved == ()
    assert armor_mundus is not None
    assert armor_mundus.total_delta > 0.0


def test_stamina_recovery_uses_canonical_514_base() -> None:
    assert BASE_STAMINA_RECOVERY == 514.0
