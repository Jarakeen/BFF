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


def test_house_stacks_matches_requested_numbered_pair_layout() -> None:
    house = next(
        preset for preset in formations.FORMATION_PRESETS
        if preset.key == "house_stacks"
    )
    assert house.dps_positions[1][1] < house.dps_positions[0][1]
    assert house.dps_positions[2][1] < house.dps_positions[3][1]
    assert house.dps_positions[5][1] < house.dps_positions[4][1]
    assert house.dps_positions[6][1] < house.dps_positions[7][1]
    assert house.dps_positions[3][0] < house.dps_positions[4][0]


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
