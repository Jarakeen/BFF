# service/update_service.py
"""Explicit maintenance-task orchestration for reference-data updates."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from time import perf_counter
from typing import Any, Callable


UpdateTask = Callable[[], Any]


@dataclass(frozen=True)
class UpdateTaskResult:
    """Outcome and timing information for one update task."""

    name: str
    success: bool
    duration_seconds: float
    message: str
    result: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UpdateService:
    """Register and explicitly execute data-maintenance tasks.

    Constructing or registering tasks performs no work. A task is called only
    by ``run_update`` or ``run_all``.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, UpdateTask] = {}

    def register_update(self, name: str, task: UpdateTask) -> None:
        """Register a named update task without executing it."""
        if not name or not name.strip():
            raise ValueError("Update task name must not be empty.")
        if not callable(task):
            raise TypeError("Update task must be callable.")
        if name in self._tasks:
            raise ValueError(f"Update task '{name}' is already registered.")

        self._tasks[name] = task

    def run_update(self, name: str) -> dict[str, Any]:
        """Run one registered task and return its structured result."""
        if name not in self._tasks:
            raise KeyError(f"Update task '{name}' is not registered.")

        return self._execute(name, self._tasks[name]).to_dict()

    def run_all(self) -> dict[str, Any]:
        """Run all registered tasks in registration order and return a summary."""
        results = [
            self._execute(name, task).to_dict()
            for name, task in self._tasks.items()
        ]
        successful = sum(1 for result in results if result["success"])

        return {
            "success": successful == len(results),
            "total": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "tasks": results,
        }

    def registered_updates(self) -> tuple[str, ...]:
        """Return registered task names without executing any task."""
        return tuple(self._tasks)

    @staticmethod
    def _execute(name: str, task: UpdateTask) -> UpdateTaskResult:
        started_at = perf_counter()
        try:
            result = task()
            message = result if isinstance(result, str) else "Update completed successfully."
            return UpdateTaskResult(
                name=name,
                success=True,
                duration_seconds=perf_counter() - started_at,
                message=message,
                result=result,
            )
        except Exception as error:
            return UpdateTaskResult(
                name=name,
                success=False,
                duration_seconds=perf_counter() - started_at,
                message=str(error),
            )
