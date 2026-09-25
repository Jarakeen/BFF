import pytest
from pydantic import ValidationError

from services.build_recent_state_pydantic_schema import validate_build_recent_state_payload


def _payload(**overrides):
    value = {
        "eso_class": "Arcanist",
        "vampire": False,
        "werewolf": False,
        "class_skill_lines": (),
        "class_mastery_ability_ids": (101, 202),
    }
    value.update(overrides)
    return value


def test_recent_build_state_accepts_two_unique_masteries() -> None:
    result = validate_build_recent_state_payload(_payload())
    assert result["eso_class"] == "Arcanist"
    assert result["class_mastery_ability_ids"] == (101, 202)


@pytest.mark.parametrize(
    "ids",
    [(1, 2, 3), (1, 1), (0,), (-1,)],
)
def test_recent_build_state_rejects_invalid_mastery_ids(ids) -> None:
    with pytest.raises(ValidationError):
        validate_build_recent_state_payload(_payload(class_mastery_ability_ids=ids))


def test_recent_build_state_rejects_masteries_while_subclassed() -> None:
    with pytest.raises(ValidationError):
        validate_build_recent_state_payload(
            _payload(class_skill_lines=("arcanist.herald",), class_mastery_ability_ids=(101,))
        )


def test_recent_build_state_rejects_vampire_and_werewolf_together() -> None:
    with pytest.raises(ValidationError):
        validate_build_recent_state_payload(_payload(vampire=True, werewolf=True))


def test_recent_build_state_forbids_unexpected_fields_and_coercion() -> None:
    with pytest.raises(ValidationError):
        validate_build_recent_state_payload({**_payload(), "mystery": "vibes"})
    with pytest.raises(ValidationError):
        validate_build_recent_state_payload(_payload(vampire="yes"))
