"""In-memory log stream for SSE realtime log endpoint."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

_queues: set[asyncio.Queue] = set()


def subscribe_logs() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _queues.add(q)
    return q


def unsubscribe_logs(q: asyncio.Queue) -> None:
    _queues.discard(q)


class SSELogHandler(logging.Handler):
    """Logging handler that fans out to SSE subscribers."""

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "msg": self.format(record),
        }
        for q in list(_queues):
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                pass


_handler: Optional[SSELogHandler] = None


def install_log_handler() -> None:
    global _handler
    if _handler is not None:
        return
    _handler = SSELogHandler()
    _handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(name)s: %(message)s")
    _handler.setFormatter(formatter)
    logging.getLogger().addHandler(_handler)
