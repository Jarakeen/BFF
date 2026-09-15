from __future__ import annotations

"""Retired compatibility installer for the old OperationsConsole context swap.

OperationsConsole builds CharacterProgression with attribute allocation only and does
not provide explicit racial passive ranks. Phase5BuildCalculationContextFactory falls
back to the normal BuildCalculationContextFactory behavior when passive ranks are
unknown, so replacing OperationsConsole.__init__ at runtime added architecture debt
without changing the overview calculation.

The entry point remains temporarily because app.py still calls it during startup. It is
intentionally inert and may be removed with the remaining legacy startup installers.
"""


_INSTALLED = False


def install() -> None:
    """Preserve the startup entry point without mutating OperationsConsole."""
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
