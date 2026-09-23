import asyncio
import logging
from collections.abc import Coroutine
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class RunRegistry:
    def __init__(self) -> None:
        self._tasks: dict[UUID, asyncio.Task[Any]] = {}

    def spawn(self, run_id: UUID, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        task = asyncio.create_task(coro, name=f"run-{run_id}")
        self._tasks[run_id] = task
        task.add_done_callback(lambda t: self._on_done(run_id, t))
        return task

    def _on_done(self, run_id: UUID, task: asyncio.Task[Any]) -> None:
        self._tasks.pop(run_id, None)
        if not task.cancelled() and task.exception() is not None:
            logger.error("background task for run %s crashed", run_id, exc_info=task.exception())

    def is_running(self, run_id: UUID) -> bool:
        return run_id in self._tasks

    @property
    def active_count(self) -> int:
        return len(self._tasks)

    async def wait_all(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

    async def cancel_all(self) -> None:
        for task in list(self._tasks.values()):
            task.cancel()
        await self.wait_all()
