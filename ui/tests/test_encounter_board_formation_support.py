from __future__ import annotations

from dataclasses import dataclass

from ui import encounter_board_formation_support as formations


@dataclass
class _Point:
    _x: float
    _y: float

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y


class _Token:
    def __init__(self, kind: str, label: str, x: float = 0.0, y: float = 0.0):
        self.kind = kind
        self.label = label
        self._point = _Point(x, y)

    def pos(self) -> _Point:
        return self._point

    def setPos(self, x: float, y: float) -> None:
        self._point = _Point(x, y)

    def update(self) -> None:
        pass


class _Viewport:
    def update(self) -> None:
        pass


class _View:
    def viewport(self) -> _Viewport:
        return _Viewport()


class _Scene:
    def update(self) -> None:
        pass


class _Board:
    def __init__(self, tokens: list[_Token] | None = None):
        self.tokens = list(tokens or [])
        self._counts = {"dps": 0, "healer": 0}
        self.scene = _Scene()
        self.view = _View()

    def _token_items(self):
        return list(self.tokens)

    def _add_token(self, kind: str, label: str, x: float, y: float):
        token = _Token(kind, label, x, y)
        self.tokens.append(token)
        return token


def test_house_and_rainbow_presets_have_expected_role_counts() -> None:
    assert [preset.key for preset in formations.FORMATION_PRESETS] == [
        "house_stacks",
        "rainbow_stacks",
    ]
    for preset in formations.FORMATION_PRESETS:
        assert len(preset.dps_positions) == 8
        assert len(preset.healer_positions) == 2
        assert len(set(preset.dps_positions)) == 8


def test_house_stacks_use_canonical_top_5_to_8_bottom_1_to_4_numbering() -> None:
    house = next(
        preset for preset in formations.FORMATION_PRESETS
        if preset.key == "house_stacks"
    )
    bottom = house.dps_positions[:4]
    top = house.dps_positions[4:]

    assert [x for x, _y in bottom] == sorted(x for x, _y in bottom)
    assert [x for x, _y in top] == sorted(x for x, _y in top)
    assert {y for _x, y in bottom} == {348.07}
    assert {y for _x, y in top} == {221.93}
    assert [x for x, _y in bottom] == [x for x, _y in top]

    horizontal_gaps = [
        round(bottom[index + 1][0] - bottom[index][0], 2)
        for index in range(3)
    ]
    assert horizontal_gaps == [146.14, 146.14, 146.14]
    assert round(bottom[0][1] - top[0][1], 2) == 126.14
    assert round(formations.HOUSE_STACK_EXTRA_SPACING_SCENE_UNITS, 2) == 66.14


def test_house_stack_healers_expand_with_the_dd_formation() -> None:
    house = next(
        preset for preset in formations.FORMATION_PRESETS
        if preset.key == "house_stacks"
    )
    healer_1, healer_2 = house.healer_positions

    assert healer_1 == (333.86, 454.21)
    assert healer_2 == (626.14, 454.21)
    assert healer_1[1] > max(y for _x, y in house.dps_positions)
    assert healer_2[1] > max(y for _x, y in house.dps_positions)


def test_rainbow_stacks_have_four_front_and_four_back_dds() -> None:
    rainbow = next(
        preset for preset in formations.FORMATION_PRESETS
        if preset.key == "rainbow_stacks"
    )
    front = rainbow.dps_positions[:4]
    back = rainbow.dps_positions[4:]
    assert len(front) == 4
    assert len(back) == 4
    assert max(y for _x, y in front) < max(y for _x, y in back)




def test_rainbow_healers_are_above_the_dd_arc() -> None:
    rainbow = next(
        preset for preset in formations.FORMATION_PRESETS
        if preset.key == "rainbow_stacks"
    )
    healer_1, healer_2 = rainbow.healer_positions

    assert healer_1 == (365.0, 195.0)
    assert healer_2 == (595.0, 195.0)
    assert healer_1[1] < min(y for _x, y in rainbow.dps_positions)
    assert healer_2[1] < min(y for _x, y in rainbow.dps_positions)


def test_apply_formation_creates_missing_roles_and_keeps_extras() -> None:
    extra = _Token("dps", "Special DD", 800.0, 450.0)
    board = _Board([extra])

    assert formations.apply_formation(board, "house_stacks") is True

    dps = [token for token in board.tokens if token.kind == "dps"]
    healers = [token for token in board.tokens if token.kind == "healer"]
    assert len(dps) == 8
    assert len(healers) == 2
    assert extra in dps


def test_unknown_formation_is_rejected_without_mutation() -> None:
    token = _Token("dps", "DD 1", 1.0, 2.0)
    board = _Board([token])

    assert formations.apply_formation(board, "not-a-shape") is False
    assert token.pos().x() == 1.0
    assert token.pos().y() == 2.0
