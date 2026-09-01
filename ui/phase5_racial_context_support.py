from __future__ import annotations

from engine.config import DEFAULT_DATABASE
from minmax.gear_set_repository import GearSetRepository
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from minmax.race_repository import RaceRepository

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.operations_console import OperationsConsole

    original_init = OperationsConsole.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.context_factory = Phase5BuildCalculationContextFactory(
            calculator=self.calculator,
            race_repository=RaceRepository(DEFAULT_DATABASE),
            gear_set_repository=GearSetRepository(DEFAULT_DATABASE),
        )

    OperationsConsole.__init__ = patched_init
    _INSTALLED = True
