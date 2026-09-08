from pathlib import Path

from ui import extreme_optimization_support


def test_extreme_page_uses_completed_blueprint_service() -> None:
    source = Path(extreme_optimization_support.__file__).read_text(encoding="utf-8")

    assert "from services.extreme_complete_blueprint_service import ExtremeCompleteBlueprintService" in source
    assert "page.blueprint_service = ExtremeCompleteBlueprintService()" in source
