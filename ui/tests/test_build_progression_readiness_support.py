from pathlib import Path

from minmax.resource_costs import ResourceType
from services.rotation_progression_readiness_service import RotationProgressionReadiness
from ui import build_progression_readiness_support
from ui import build_progression_scroll_fix


def _result(
    *,
    resource: ResourceType,
    owned=(),
    equipped=(),
    relevant=(),
    missing=(),
    unresolved=(),
    character_id="char-magrat",
):
    return RotationProgressionReadiness(
        character_id=character_id,
        resource=resource,
        canonical_owned_skill_lines=tuple(owned),
        equipped_armor_skill_lines=tuple(equipped),
        cost_relevant_skill_lines=tuple(relevant),
        missing_cost_relevant_skill_lines=tuple(missing),
        unresolved=tuple(unresolved),
    )


def test_readiness_text_names_missing_canonical_armor_line() -> None:
    result = _result(
        resource=ResourceType.MAGICKA,
        equipped=("Light Armor", "Medium Armor"),
        relevant=("Light Armor",),
        missing=("Light Armor",),
        unresolved=("Canonical character progression has no owned skill lines recorded",),
    )

    assert build_progression_readiness_support._readiness_text(result) == (
        "Magicka cost readiness: BLOCKED, missing canonical ownership: Light Armor"
    )


def test_status_text_keeps_equipment_as_evidence_only() -> None:
    magicka = _result(
        resource=ResourceType.MAGICKA,
        owned=("Light Armor", "Medium Armor"),
        equipped=("Light Armor", "Medium Armor"),
        relevant=("Light Armor",),
    )
    stamina = _result(
        resource=ResourceType.STAMINA,
        owned=("Light Armor", "Medium Armor"),
        equipped=("Light Armor", "Medium Armor"),
        relevant=("Medium Armor",),
    )

    text = build_progression_readiness_support._status_text(magicka, stamina)

    assert "Magicka cost readiness: READY" in text
    assert "Stamina cost readiness: READY" in text
    assert "Current build evidence: Light Armor, Medium Armor equipped" in text
    assert "Equipment is evidence only" in text
    assert "all builds" in text


def test_progression_scroll_fix_installs_readiness_after_scroll_patch() -> None:
    source = Path(build_progression_scroll_fix.__file__).read_text(encoding="utf-8")

    scroll_assignment = source.index(
        "BuildsPage._load_progression_tab = load_progression_without_inner_scroll"
    )
    readiness_install = source.index("install_progression_readiness()")

    assert readiness_install > scroll_assignment
