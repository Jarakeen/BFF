from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.stat_ids import StatId
from services.extreme_complete_blueprint_service import ExtremeCompleteBlueprintService
from services.extreme_complete_optimization_service import CRITICAL_HEALING_OBJECTIVE


def test_critical_healing_set_score_uses_critical_healing_not_healing_done() -> None:
    service = ExtremeCompleteBlueprintService.__new__(ExtremeCompleteBlueprintService)
    service.extreme = SimpleNamespace(
        gear_set_repository=SimpleNamespace(
            get_set=lambda name: SimpleNamespace(id=42) if name == "Healer Set" else None
        )
    )
    service.set_effects = SimpleNamespace(
        resolve_effects=lambda set_id, pieces: (
            SimpleNamespace(stat=StatId.CRITICAL_HEALING, value=0.12),
            SimpleNamespace(stat=StatId.HEALING_DONE, value=0.30),
        )
    )

    score = service._set_static_score("Healer Set", CRITICAL_HEALING_OBJECTIVE)

    assert score == pytest.approx(0.12)
