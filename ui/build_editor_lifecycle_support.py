from __future__ import annotations

"""Explicit composition seam for BuildEditor lifecycle extensions.

Historically BuildEditor features wrapped ``__init__``, ``load``, and ``model``
independently at startup. That made behavior depend on installer order. This
module keeps one runtime wrapper per lifecycle boundary and lets features
register deterministic hooks while the remaining legacy wrappers are migrated
incrementally.
"""

from collections.abc import Callable
from typing import Any

_INSTALLED = False
_POST_INIT_HOOKS: dict[str, Callable[[Any], None]] = {}
_PRE_LOAD_HOOKS: dict[str, Callable[[Any, Any], None]] = {}
_POST_LOAD_HOOKS: dict[str, Callable[[Any, Any], None]] = {}
_MODEL_POST_HOOKS: dict[str, Callable[[Any, Any], None]] = {}


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from widgets.build_editor import BuildEditor

    original_init = BuildEditor.__init__
    original_load = BuildEditor.load
    original_model_getter = BuildEditor.model.fget

    def init_composed(self, *args, **kwargs) -> None:
        original_init(self, *args, **kwargs)
        for hook in tuple(_POST_INIT_HOOKS.values()):
            hook(self)

    def load_composed(self, model) -> None:
        for hook in tuple(_PRE_LOAD_HOOKS.values()):
            hook(self, model)
        original_load(self, model)
        for hook in tuple(_POST_LOAD_HOOKS.values()):
            hook(self, model)

    def model_composed(self):
        build = original_model_getter(self)
        for hook in tuple(_MODEL_POST_HOOKS.values()):
            hook(self, build)
        return build

    BuildEditor.__init__ = init_composed
    BuildEditor.load = load_composed
    BuildEditor.model = property(model_composed)
    _INSTALLED = True


def register_post_init(key: str, hook: Callable[[Any], None]) -> None:
    install()
    _POST_INIT_HOOKS[str(key)] = hook


def register_pre_load(key: str, hook: Callable[[Any, Any], None]) -> None:
    install()
    _PRE_LOAD_HOOKS[str(key)] = hook


def register_post_load(key: str, hook: Callable[[Any, Any], None]) -> None:
    install()
    _POST_LOAD_HOOKS[str(key)] = hook


def register_model_post(key: str, hook: Callable[[Any, Any], None]) -> None:
    install()
    _MODEL_POST_HOOKS[str(key)] = hook


__all__ = [
    "install",
    "register_post_init",
    "register_pre_load",
    "register_post_load",
    "register_model_post",
]
