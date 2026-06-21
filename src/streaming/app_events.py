from __future__ import annotations

import asyncio
from typing import Any


_EVENT_QUEUES: dict[str, asyncio.Queue[dict[str, Any]]] = {}


def register_app_event_queue(trace_id: str) -> asyncio.Queue[dict[str, Any]]:
    """Register one app-level event queue for a request trace."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _EVENT_QUEUES[trace_id] = queue
    return queue


def unregister_app_event_queue(trace_id: str) -> None:
    """Remove the app-level event queue for a request trace."""
    _EVENT_QUEUES.pop(trace_id, None)


def publish_app_event(trace_id: str | None, event: dict[str, Any]) -> bool:
    """Publish an app-level event to the active SSE stream, if any."""
    if not trace_id:
        return False
    queue = _EVENT_QUEUES.get(trace_id)
    if queue is None:
        return False
    queue.put_nowait(event)
    return True
