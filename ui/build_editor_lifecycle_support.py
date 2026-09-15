from __future__ import annotations

"""Explicit composition seam for BuildEditor load/model extensions.

Historically BuildEditor features wrapped ``load`` and ``model`` independently at
startup.  That made behavior depend on installer order.  This module keeps one
runtime wrapper and lets features register deterministic before/after hooks while
the remaining legacy wrappers are migrated incrementally.
"""

from collections.abc import Callable
from typing import Any

_INSTALLED = False
_PRE_LOAD_HOOKS: dict[str, Callable[[Any, Any], None]] = {}
_POST_LOAD_HOOKS: dict[str, Callable[[Any, Any], None]] = {}
_MODEL_POST_HOOKS: dict[str, Callable[[Any, Any], None]] = {}


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from widgets.build_editor import BuildEditor

    original_load = BuildEditor.load
    original_model_getter = BuildEditor.model.fget

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

    BuildEditor.load = load_composed
    BuildEditor.model = property(model_composed)
    _INSTALLED = True


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
    "register_pre_load",
    "register_post_load",
    "register_model_post",
]
