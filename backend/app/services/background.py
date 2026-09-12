from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Simple async background job queue for production processing."""

    def __init__(self, *, worker_count: int = 2, queue_size: int = 100) -> None:
        self.worker_count = worker_count
        self.queue: asyncio.Queue[Coroutine[Any, Any, Any] | None] = asyncio.Queue(maxsize=queue_size)
        self.workers: list[asyncio.Task[None]] = []
        self.started = False

    def configure(self, worker_count: int, queue_size: int) -> None:
        self.worker_count = worker_count
        self.queue = asyncio.Queue(maxsize=queue_size)

    async def start(self) -> None:
        if self.started:
            return
        self.started = True
        for _ in range(self.worker_count):
            task = asyncio.create_task(self._worker())
            self.workers.append(task)
        logger.info("started %d background workers", self.worker_count)

    async def stop(self) -> None:
        if not self.started:
            return
        for _ in self.workers:
            await self.queue.put(None)
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        self.started = False
        logger.info("stopped background workers")

    async def _worker(self) -> None:
        while True:
            coro = await self.queue.get()
            if coro is None:
                break
            try:
                await coro
            except Exception as exc:
                logger.exception("background job failed: %s", exc)
            finally:
                self.queue.task_done()

    def submit(self, coro: Coroutine[Any, Any, Any]) -> None:
        if not self.started:
            logger.warning("background manager not started, running task inline")
            asyncio.create_task(coro)
            return

        try:
            self.queue.put_nowait(coro)
        except asyncio.QueueFull:
            logger.warning("background job queue full, running task inline")
            asyncio.create_task(coro)


background_manager = BackgroundTaskManager()
