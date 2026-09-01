from __future__ import annotations

"""Phase 5 bridge from saved builds into character-owned MinMax progression."""

from models.build_model import PlayerBuild
from services.minmax_character_progression_adapter import MinmaxCharacterProgressionAdapter

_INSTALLED = False


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    from ui.operations_console import OperationsConsole

    def progression_for(self, build: PlayerBuild):
        adapter = MinmaxCharacterProgressionAdapter(
            self.build_service.canonical.catalog_service
        )
        return adapter.resolve(build).progression

    OperationsConsole._progression_for = progression_for
    _INSTALLED = True
