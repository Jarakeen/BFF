import json
from pathlib import Path

from services.narrator_service import NarratorService


def test_narrator_service_loads_json_runtime_categories(tmp_path: Path) -> None:
    content = tmp_path / "narrator.json"
    content.write_text(
        json.dumps({"General": ["Observation one."], "Wipes": ["Experiment concluded."]}),
        encoding="utf-8",
    )

    narrator = NarratorService(content)

    assert narrator.categories() == ["General", "Wipes"]
    assert narrator.pick("General") == "Observation one."


def test_narrator_service_keeps_markdown_backward_compatibility(tmp_path: Path) -> None:
    content = tmp_path / "narrator.md"
    content.write_text("## General\n\n- Observation one.\n", encoding="utf-8")

    narrator = NarratorService(content)

    assert narrator.categories() == ["General"]
    assert narrator.pick("General") == "Observation one."
