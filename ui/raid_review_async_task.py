from __future__ import annotations

"""Small Qt worker used to keep Raid Review network work off the GUI thread."""

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal


class RaidReviewAsyncTask(QThread):
    """Run one callable on a worker thread and marshal its result back to Qt."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, operation: Callable[[], object], parent=None) -> None:
        super().__init__(parent)
        self._operation = operation

    def run(self) -> None:
        try:
            result = self._operation()
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)


__all__ = ["RaidReviewAsyncTask"]
