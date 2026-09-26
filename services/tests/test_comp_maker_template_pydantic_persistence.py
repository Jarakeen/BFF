from __future__ import annotations

from pathlib import Path

import pytest

from services.comp_maker_template_service import CompMakerTemplate, CompMakerTemplateService
from services.planning_artifact_pydantic_schema import validate_comp_maker_template


def _template() -> CompMakerTemplate:
    return CompMakerTemplate(
        template_id="template-1",
        name="Z'enKosh",
        role="DD",
        eso_class="Dragonknight",
        gear_sets=("Z'en's Redress", "Roar of Alkosh"),
        skills=("Engulfing Flames",),
        mundus="The Thief",
        notes="Support DD",
    )


def test_comp_maker_template_round_trips_exactly(tmp_path: Path) -> None:
    service = CompMakerTemplateService(tmp_path / "foundrydock.db")
    expected = _template()

    assert service.save(expected) == expected
    assert service.list_templates() == (expected,)


def test_comp_maker_template_rejects_invalid_payload_before_mutation(tmp_path: Path) -> None:
    service = CompMakerTemplateService(tmp_path / "foundrydock.db")
    service.save(_template())

    invalid = CompMakerTemplate(template_id="template-2", name="", role="DD")
    with pytest.raises(ValueError):
        service.save(invalid)

    assert service.list_templates() == (_template(),)


def test_comp_maker_template_schema_rejects_duplicate_gear() -> None:
    with pytest.raises(ValueError):
        validate_comp_maker_template({
            "template_id": "template-1",
            "name": "Duplicate",
            "role": "DD",
            "eso_class": "Dragonknight",
            "gear_sets": ("Z'en's Redress", "z'en's redress"),
            "skills": (),
            "mundus": "",
            "notes": "",
            "source_build_id": "",
            "source_plan_name": "",
            "source_seat_id": "",
        })
