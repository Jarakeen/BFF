import pytest

from minmax.coverage_requirement import CoverageRequirement
from minmax.encounter_requirements import EncounterRequirementSet
from minmax.role import Role


def _requirement(
    effect_name: str,
    *,
    required_roles: frozenset[Role] = frozenset(),
) -> CoverageRequirement:
    return CoverageRequirement(
        effect_name=effect_name,
        required_roles=required_roles,
    )


def test_requirement_set_preserves_encounter_identity():
    requirements = EncounterRequirementSet(
        encounter_id="rockgrove_hm",
        encounter_name="Rockgrove Hard Mode",
        requirements=(
            _requirement("major_courage"),
        ),
    )

    assert requirements.encounter_id == "rockgrove_hm"
    assert requirements.encounter_name == "Rockgrove Hard Mode"


def test_requirement_set_returns_all_requirements():
    requirements = EncounterRequirementSet(
        encounter_id="sunspire",
        encounter_name="Sunspire",
        requirements=(
            _requirement("major_courage"),
            _requirement("major_force"),
            _requirement("major_slayer"),
        ),
    )

    assert requirements.all() == (
        requirements.for_effect("major_courage"),
        requirements.for_effect("major_force"),
        requirements.for_effect("major_slayer"),
    )


def test_requirement_set_can_find_requirement_by_effect():
    requirement = _requirement("major_force")

    requirements = EncounterRequirementSet(
        encounter_id="sunspire",
        encounter_name="Sunspire",
        requirements=(requirement,),
    )

    assert requirements.for_effect("major_force") == requirement
    assert requirements.for_effect("missing_effect") is None


def test_required_effect_names_preserve_requirement_order():
    requirements = EncounterRequirementSet(
        encounter_id="test",
        encounter_name="Test Encounter",
        requirements=(
            _requirement("major_force"),
            _requirement("major_courage"),
            _requirement("major_slayer"),
        ),
    )

    assert requirements.required_effect_names() == (
        "major_force",
        "major_courage",
        "major_slayer",
    )


def test_for_role_returns_only_explicit_role_requirements():
    requirements = EncounterRequirementSet(
        encounter_id="test",
        encounter_name="Test Encounter",
        requirements=(
            _requirement(
                "major_courage",
                required_roles=frozenset({Role.HEALER}),
            ),
            _requirement(
                "major_slayer",
                required_roles=frozenset({Role.DD}),
            ),
            _requirement("minor_courage"),
        ),
    )

    assert requirements.for_role(Role.HEALER) == (
        requirements.for_effect("major_courage"),
    )

    assert requirements.for_role(Role.DD) == (
        requirements.for_effect("major_slayer"),
    )

    assert requirements.for_role(Role.TANK) == ()


def test_requirement_count_reports_distinct_requirements():
    requirements = EncounterRequirementSet(
        encounter_id="test",
        encounter_name="Test Encounter",
        requirements=(
            _requirement("major_courage"),
            _requirement("major_force"),
        ),
    )

    assert requirements.requirement_count == 2


def test_empty_encounter_is_allowed():
    requirements = EncounterRequirementSet(
        encounter_id="test",
        encounter_name="Test Encounter",
        requirements=(),
    )

    assert requirements.all() == ()
    assert requirements.required_effect_names() == ()
    assert requirements.requirement_count == 0


def test_duplicate_effect_requirements_are_rejected():
    with pytest.raises(ValueError):
        EncounterRequirementSet(
            encounter_id="test",
            encounter_name="Test Encounter",
            requirements=(
                _requirement("major_courage"),
                _requirement("major_courage"),
            ),
        )


def test_empty_encounter_id_is_rejected():
    with pytest.raises(ValueError):
        EncounterRequirementSet(
            encounter_id="",
            encounter_name="Test Encounter",
            requirements=(),
        )


def test_empty_encounter_name_is_rejected():
    with pytest.raises(ValueError):
        EncounterRequirementSet(
            encounter_id="test",
            encounter_name="",
            requirements=(),
        )
