"""Structured timing events for runtime performance analysis.

The logger still writes normal text logs, but every record emitted by this
module starts with ``AI_TUTOR_TIMING`` followed by one JSON object. This keeps
human logs readable while making step-level timing easy to parse later.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from google.adk.agents.invocation_context import InvocationContext

from src.logger import logger


TIMING_LOG_PREFIX = "AI_TUTOR_TIMING"
TRACE_ID_STATE_KEY = "timing_trace_id"


def make_trace_id(uid: str, sid: str) -> str:
    """Create a short trace id for one user request."""
    return f"{uid}:{sid}:{uuid.uuid4().hex[:8]}"


def get_trace_id_from_state(state: dict[str, Any] | None) -> str | None:
    """Return the request trace id stored in session state, if present."""
    if not state:
        return None
    value = state.get(TRACE_ID_STATE_KEY)
    return str(value) if value else None


def timing_context_from_invocation(ctx: InvocationContext) -> dict[str, str | None]:
    """Build common timing fields from an ADK invocation context."""
    state = ctx.session.state if ctx.session else {}
    return {
        "trace_id": get_trace_id_from_state(state),
        "uid": str(getattr(ctx.session, "user_id", "") or state.get("uid") or "") or None,
        "sid": str(getattr(ctx.session, "id", "") or state.get("sid") or "") or None,
        "invocation_id": str(getattr(ctx, "invocation_id", "") or "") or None,
    }


def compact_text(value: Any, max_len: int = 180) -> str:
    """Return a compact single-line representation of a value."""
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}...<truncated chars={len(text)}>"


def summarize_payload(value: Any, *, max_string_len: int = 180, max_items: int = 8) -> Any:
    """Summarize payload values so timing logs do not contain large artifacts."""
    if value is None or isinstance(value, bool | int | float):
        return value

    if isinstance(value, str):
        if len(value) <= max_string_len:
            return value
        return {
            "type": "str",
            "chars": len(value),
            "preview": compact_text(value, max_string_len),
        }

    if isinstance(value, bytes):
        return {"type": "bytes", "bytes": len(value)}

    if isinstance(value, dict):
        summarized: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                summarized["__truncated__"] = len(value) - max_items
                break
            summarized[str(key)] = summarize_payload(
                item,
                max_string_len=max_string_len,
                max_items=max_items,
            )
        return summarized

    if isinstance(value, list | tuple | set):
        sequence = list(value)
        return {
            "type": type(value).__name__,
            "len": len(sequence),
            "items": [
                summarize_payload(
                    item,
                    max_string_len=max_string_len,
                    max_items=max_items,
                )
                for item in sequence[:max_items]
            ],
        }

    return compact_text(value, max_string_len)


def build_timing_record(
    *,
    event: str,
    stage: str,
    name: str,
    trace_id: str | None = None,
    uid: str | None = None,
    sid: str | None = None,
    invocation_id: str | None = None,
    status: str | None = None,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a normalized timing record."""
    record: dict[str, Any] = {
        "event": event,
        "stage": stage,
        "name": name,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
    }
    optional_values = {
        "trace_id": trace_id,
        "uid": uid,
        "sid": sid,
        "invocation_id": invocation_id,
        "status": status,
        "duration_ms": round(duration_ms, 3) if duration_ms is not None else None,
        "metadata": summarize_payload(metadata) if metadata else None,
    }
    for key, value in optional_values.items():
        if value is not None:
            record[key] = value
    return record


def log_timing_event(
    *,
    event: str,
    stage: str,
    name: str,
    trace_id: str | None = None,
    uid: str | None = None,
    sid: str | None = None,
    invocation_id: str | None = None,
    status: str | None = None,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write one structured timing event and return the emitted record."""
    record = build_timing_record(
        event=event,
        stage=stage,
        name=name,
        trace_id=trace_id,
        uid=uid,
        sid=sid,
        invocation_id=invocation_id,
        status=status,
        duration_ms=duration_ms,
        metadata=metadata,
    )
    logger.info(
        "{} {}",
        TIMING_LOG_PREFIX,
        json.dumps(record, ensure_ascii=False, sort_keys=True),
    )
    return record


@contextmanager
def timing_stage(
    stage: str,
    name: str,
    *,
    trace_id: str | None = None,
    uid: str | None = None,
    sid: str | None = None,
    invocation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Measure one stage and write start/end timing records."""
    dynamic_metadata: dict[str, Any] = {}
    start = time.perf_counter()
    log_timing_event(
        event="stage_start",
        stage=stage,
        name=name,
        trace_id=trace_id,
        uid=uid,
        sid=sid,
        invocation_id=invocation_id,
        metadata=metadata,
    )
    try:
        yield dynamic_metadata
    except Exception as exc:
        dynamic_metadata["error_type"] = type(exc).__name__
        dynamic_metadata["error"] = compact_text(str(exc))
        merged_metadata = {**(metadata or {}), **dynamic_metadata}
        log_timing_event(
            event="stage_end",
            stage=stage,
            name=name,
            trace_id=trace_id,
            uid=uid,
            sid=sid,
            invocation_id=invocation_id,
            status="error",
            duration_ms=(time.perf_counter() - start) * 1000,
            metadata=merged_metadata,
        )
        raise
    else:
        status = str(dynamic_metadata.pop("status", "success"))
        merged_metadata = {**(metadata or {}), **dynamic_metadata}
        log_timing_event(
            event="stage_end",
            stage=stage,
            name=name,
            trace_id=trace_id,
            uid=uid,
            sid=sid,
            invocation_id=invocation_id,
            status=status,
            duration_ms=(time.perf_counter() - start) * 1000,
            metadata=merged_metadata,
        )
